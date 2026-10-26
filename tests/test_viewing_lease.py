"""Real coordinator with fake transport/clock; no live HA or lamp access."""
import asyncio,copy,math,unittest
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock
import test_recovery as r

r.ctx['dt_util']=SimpleNamespace(utc_from_timestamp=lambda t:datetime.fromtimestamp(t,timezone.utc),as_local=lambda d:d.astimezone(ZoneInfo('Asia/Shanghai')))
protocol=r.protocol

def frame(boundaries=(540,600,720,1200,1320,0),fields=(26,10,26,12,0,0),code=None):
 def bcd(x):return (x//10)*16+x%10
 times=[]
 for i,b in enumerate(boundaries):times.extend([b]*(2 if 0<i<5 else 1))
 payload=b'LED001'+bytes(bcd(x)for x in fields)+b''.join(bytes([bcd(x//60),bcd(x%60)])for x in times)+bytes([20]*20)
 payload+=bytes(141-len(payload))
 value=bytearray(protocol.build_frame(protocol.CMD_READ_CONFIG,payload,device_code=code or protocol.DEFAULT_DEVICE_CODE));value[0]=protocol.RESPONSE_HEADER;return bytes(value)

def mutate(value,index,number):
 b=bytearray(value);b[index]=number;b[-2]=protocol._xor(b[1:-2]);return bytes(b)

class TimingParserTests(unittest.TestCase):
 def test_captured_reply_exact_clock_and_boundaries(self):
  value=bytes.fromhex('DD009301023A01104145444334352610210043270900100010001200120020002000220022000000040E1E0C081C3C181446963C0C2A5A2406152D1205010000000101FFFFFFFF000000522240303130303030303030333030303030313031303330303030303030303030303030303030303030303030303030303030303030303030303030313030222C227A65746C696768742248CC')
  s=protocol.parse_schedule_timing(value);self.assertEqual(s.boundaries,(540,600,720,1200,1320,0));self.assertEqual(s.clock_fields,(26,10,21,0,43,27))
 def test_invalid_and_ambiguous_inputs_rejected(self):
  for value in [frame(code=b'BAD!'),mutate(frame(),20,0x2A),mutate(frame(),24,0x11),frame(fields=(26,2,31,12,0,0)),frame(boundaries=(540,600,500,700,800,900)),frame(boundaries=(0,0,0,0,0,0)),mutate(frame(),20,0x24),frame()[:-2]]:
   with self.subTest(hex=value[:24].hex()),self.assertRaises(ValueError):protocol.parse_schedule_timing(value)
 def test_checksum_and_shifted_layout_rejected(self):
  bad=bytearray(frame());bad[-2]^=1
  with self.assertRaises(ValueError):protocol.parse_schedule_timing(bytes(bad))
  # A structurally valid frame with an extra header byte must not be offset-scanned.
  payload=frame()[8:-2];b=bytearray(protocol.build_frame(protocol.CMD_READ_CONFIG,payload[:12]+b'\0'+payload[12:]));b[0]=protocol.RESPONSE_HEADER
  with self.assertRaises(ValueError):protocol.parse_schedule_timing(bytes(b))

class ViewingLeaseTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):r.Store.saved={};r.timers.clear();r.clock.now=1000
 def make(self):return r.RecoveryTests.make(self)
 def timing(self,c,local='2026-10-26T23:50:00+08:00',bounds=(1380,1435,5,55,115,175)):
  d=datetime.fromisoformat(local);r.clock.now=d.timestamp();c.schedule_timing=protocol.ScheduleTiming(bounds,(d.year-2000,d.month,d.day,d.hour,d.minute,d.second));c.schedule_timing_read_at=r.clock.now
 async def test_cap_persisted_and_idempotent_enable_never_renews(self):
  c,_=self.make();await c.async_viewing_set(True);self.assertEqual(c._viewing_deadline,2800)
  r.clock.now=1100;await c.async_viewing_set(True);self.assertEqual(c._viewing_deadline,2800)
  self.assertEqual(r.Store.saved[c._feeding_store.key]['viewing_deadline'],2800)
 async def test_verified_boundary_precedes_cap_and_midnight_works(self):
  c,_=self.make();self.timing(c);start=r.clock.now;await c.async_viewing_set(True);self.assertEqual(c._viewing_deadline,start+300)
  c,_=self.make();self.timing(c,'2026-10-26T23:55:00+08:00');start=r.clock.now;await c.async_viewing_set(True);self.assertEqual(c._viewing_deadline,start+600)
 async def test_stale_unknown_and_wrong_clock_use_cap(self):
  for kind in ['stale','future','clock_skew','missing']:
   c,_=self.make();self.timing(c)
   if kind=='stale':c.schedule_timing_read_at-=91
   if kind=='future':c.schedule_timing_read_at+=1
   if kind=='clock_skew':c.schedule_timing=protocol.ScheduleTiming(c.schedule_timing.boundaries,(26,10,26,22,50,0))
   if kind=='missing':c.schedule_timing=None
   await c.async_viewing_set(True);self.assertEqual(c._viewing_deadline,r.clock.now+1800)
 async def test_restore_keeps_deadline_without_new_thirty_minutes(self):
  c,_=self.make();await c.async_viewing_set(True);await c.async_shutdown();r.clock.now=1500
  other,_=self.make();await other.async_restore_feeding();self.assertTrue(other.viewing_on);self.assertEqual(other._viewing_deadline,2800);self.assertEqual(r.timers[-1][0],1300)
 async def test_expired_restore_drops_viewing_and_resumes_current_schedule(self):
  c,_=self.make();await c.async_viewing_set(True);r.clock.now=3000
  other,_=self.make();await other.async_restore_feeding();self.assertFalse(other.viewing_on);other.client.async_turn_on.assert_awaited_once()
 async def test_bad_or_legacy_saved_lease_cannot_become_unbounded(self):
  for changes in [{'viewing_started_at':None,'viewing_deadline':None},{'viewing_deadline':float('nan')},{'viewing_deadline':99999999},{'viewing_started_at':1100},{'viewing_deadline':True}]:
   c,_=self.make();await c.async_viewing_set(True);r.Store.saved[c._feeding_store.key].update(changes)
   other,_=self.make();await other.async_restore_feeding();self.assertFalse(other.viewing_on)
 async def test_auto_expiry_normal_schedule_and_failed_resume_recover(self):
  c,_=self.make();await c.async_viewing_set(True);deadline=c._viewing_deadline;r.clock.now=deadline
  c.client.async_turn_on.side_effect=OSError('offline')
  with self.assertRaises(OSError):await c.async_expire_viewing(deadline)
  self.assertFalse(c.viewing_on);self.assertTrue(r.Store.saved[c._feeding_store.key]['recovery_pending'])
  other,_=self.make();await other.async_restore_feeding();self.assertFalse(r.Store.saved[c._feeding_store.key]['recovery_pending'])
 async def test_feeding_priority_at_expiry_does_not_send_any_light_command(self):
  c,_=self.make();await c.async_viewing_set(True);deadline=c._viewing_deadline;await c.async_feeding_set(True)
  c.client.async_turn_on.reset_mock();c.client.async_turn_off.reset_mock();c.client.async_set_brightness.reset_mock();r.clock.now=deadline
  await c.async_expire_viewing(deadline);self.assertTrue(c.feeding_on);self.assertFalse(c.viewing_on)
  c.client.async_turn_on.assert_not_awaited();c.client.async_turn_off.assert_not_awaited();c.client.async_set_brightness.assert_not_awaited()
 async def test_manual_off_clears_lease_and_late_expiry_cannot_relight(self):
  c,_=self.make();await c.async_viewing_set(True);deadline=c._viewing_deadline;await c.async_user_off();c.client.async_turn_on.reset_mock();r.clock.now=deadline
  await c.async_expire_viewing(deadline);c.client.async_turn_on.assert_not_awaited();self.assertEqual(c.active_mode,'off');self.assertIsNone(c._viewing_deadline)
  await c.async_resume_schedule();self.assertEqual(c.active_mode,'schedule')
 async def test_off_refuses_hidden_viewing_and_explicit_on_drops_old_view(self):
  c,_=self.make();await c.async_user_off()
  with self.assertRaises(RuntimeError):await c.async_viewing_set(True)
  self.assertFalse(c.viewing_on);await c.async_resume_schedule();await c.async_viewing_set(True);await c.async_resume_schedule();self.assertFalse(c.viewing_on)
 async def test_stale_callback_does_not_end_new_session_and_shutdown_is_inert(self):
  c,tasks=self.make();await c.async_viewing_set(True);old=c._viewing_deadline;await c.async_viewing_set(False);r.clock.now=1100;await c.async_viewing_set(True);new=c._viewing_deadline;r.clock.now=old
  await c.async_expire_viewing(old);self.assertTrue(c.viewing_on);self.assertEqual(c._viewing_deadline,new)
  cancel=c._viewing_unsub;await c.async_shutdown();cancel.assert_called_once();c._viewing_timeout(new);self.assertFalse(tasks)
 async def test_refresh_can_only_shorten_and_does_not_write_output(self):
  c,_=self.make();self.timing(c);c.schedule_timing=None;await c.async_viewing_set(True);old=c._viewing_deadline;self.timing(c)
  c.client.async_set_brightness.reset_mock();await c._shorten_viewing_deadline();self.assertLess(c._viewing_deadline,old);c.client.async_set_brightness.assert_not_awaited()
  deadline=c._viewing_deadline;c.schedule_timing=None;await c._shorten_viewing_deadline();self.assertEqual(c._viewing_deadline,deadline)
 async def test_expired_during_feeding_restart_preserves_feeding(self):
  c,_=self.make();await c.async_viewing_set(True);await c.async_feeding_set(True);r.clock.now=2800
  other,_=self.make();await other.async_restore_feeding();self.assertTrue(other.feeding_on);self.assertFalse(other.viewing_on);other.client.async_turn_on.assert_not_awaited()

 async def test_monotonic_timeout_still_expires_after_wall_clock_moves_back(self):
  c,tasks=self.make();await c.async_viewing_set(True);deadline=c._viewing_deadline;r.clock.now=900
  c._viewing_timeout(deadline);await asyncio.gather(*tasks);self.assertFalse(c.viewing_on)
 async def test_initial_storage_failure_arms_retry_without_sending_output(self):
  c,_=self.make();await c.async_viewing_set(True);deadline=c._viewing_deadline;r.clock.now=deadline
  c.client.async_turn_on.reset_mock();c._feeding_store.async_save=AsyncMock(side_effect=OSError('disk unavailable'))
  with self.assertRaises(OSError):await c.async_expire_viewing(deadline)
  c.client.async_turn_on.assert_not_awaited();self.assertIsNotNone(c._control_retry_unsub);self.assertIsNotNone(c.command_error)
 async def test_refresh_failure_clears_timing_instead_of_reusing_old_boundary(self):
  c,_=self.make();self.timing(c,'2026-10-26T12:00:00+08:00')
  c.client.async_read_config=AsyncMock(return_value=frame())
  await c._async_update_data();self.assertIsNotNone(c.schedule_timing)
  c.client.async_read_config.side_effect=OSError('offline')
  await c._async_update_data();self.assertIsNone(c.schedule_timing);self.assertIsNone(c.schedule_timing_read_at)
 async def test_duplicate_timeout_tasks_resume_only_once(self):
  c,tasks=self.make();await c.async_viewing_set(True);deadline=c._viewing_deadline;r.clock.now=deadline
  c.client.async_turn_on.reset_mock();c._viewing_timeout(deadline);c._viewing_timeout(deadline);await asyncio.gather(*tasks)
  c.client.async_turn_on.assert_awaited_once()
 async def test_dst_nonexistent_boundary_is_not_fabricated(self):
  previous=r.ctx['dt_util'];r.ctx['dt_util']=SimpleNamespace(utc_from_timestamp=lambda t:datetime.fromtimestamp(t,timezone.utc),as_local=lambda d:d.astimezone(ZoneInfo('America/New_York')))
  try:
   c,_=self.make();self.timing(c,'2026-03-08T01:55:00-05:00',bounds=(60,125,185,360,600,720));start=r.clock.now
   await c.async_viewing_set(True);self.assertEqual(c._viewing_deadline,start+600)
  finally:r.ctx['dt_util']=previous

 async def test_failed_view_expiry_retry_cannot_end_a_new_feeding_session(self):
  c,tasks=self.make();await c.async_viewing_set(True);deadline=c._viewing_deadline;r.clock.now=deadline
  c.client.async_turn_on.side_effect=OSError('temporary UDP failure')
  with self.assertRaises(OSError):await c.async_expire_viewing(deadline)
  retry=r.timers[-1][1];c.client.async_turn_on.side_effect=None;await c.async_feeding_set(True);feed_deadline=c._feeding_deadline
  r.clock.now+=30;retry(None);await asyncio.gather(*tasks)
  self.assertTrue(c.feeding_on);self.assertEqual(c._feeding_deadline,feed_deadline)

if __name__=='__main__':unittest.main()
