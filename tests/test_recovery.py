"""Real control classes with in-memory storage, fake clocks and UDP transport."""
import ast,asyncio,math,copy,importlib.util,logging,sys,time,unittest,random
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
from datetime import timedelta
ROOT=Path(__file__).resolve().parents[1]/'custom_components/zetlight_led'
spec=importlib.util.spec_from_file_location('recovery_protocol',ROOT/'protocol.py');protocol=importlib.util.module_from_spec(spec);sys.modules[spec.name]=protocol;spec.loader.exec_module(protocol)
class Base:
    def __class_getitem__(cls,item):return cls
    def __init__(self,hass,*args,**kwargs):self.hass=hass
    def async_update_listeners(self):pass
class Store:
    saved={}
    def __init__(self,hass,version,key):self.key=key
    async def async_save(self,value):self.saved[self.key]=copy.deepcopy(value)
    async def async_load(self):return copy.deepcopy(self.saved.get(self.key))
    async def async_remove(self):self.saved.pop(self.key,None)
clock=SimpleNamespace(now=1000)
timers=[]
def later(hass,delay,callback):
    timers.append((delay,callback));return Mock()
ctx=dict(timedelta=timedelta,math=math,asyncio=asyncio,random=random,time=SimpleNamespace(time=lambda:clock.now),protocol=protocol,Store=Store,_LOGGER=logging.getLogger('recovery'),DOMAIN='zetlight_led',SCAN_INTERVAL=timedelta(seconds=30),LIGHTNING_DEFAULT_FLASHES=1,LIGHTNING_DEFAULT_INTENSITY=80,LIGHTNING_DEFAULT_ON_MS=50,FEEDING_DEFAULT_LEVEL=20,FEEDING_DEFAULT_MINUTES=10,callback=lambda f:f,DataUpdateCoordinator=Base,HomeAssistantError=RuntimeError,async_call_later=later,ZetlightUDPError=OSError,REQUEST_TIMEOUT=.1)
tree=ast.parse((ROOT/'__init__.py').read_text());nodes=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+[x for x in tree.body if isinstance(x,ast.ClassDef) and x.name in ['ZetlightClient','ZetlightCoordinator','_EffectInterrupted']]
compiled=ast.Module(body=nodes,type_ignores=[]);ast.fix_missing_locations(compiled);exec(compile(compiled,str(ROOT/'__init__.py'),'exec'),ctx)
Coord=ctx['ZetlightCoordinator'];Client=ctx['ZetlightClient']
class FakeClient:
    def __init__(self):
        self.curve=[(80,80,80,80)]*5;self.async_turn_on=AsyncMock();self.async_turn_off=AsyncMock();self.async_set_brightness=AsyncMock();self.async_read_status=AsyncMock(return_value=SimpleNamespace(setpoints=[80]*4));self.async_read_options=AsyncMock(return_value=SimpleNamespace(fade_enable=False));self.async_set_fade=AsyncMock();self.fail=False
    async def async_write_schedule(self,slots,start,durations):
        if self.fail:raise OSError('UDP failed after time write')
        self.curve=slots
    async def async_write_brightness(self,slots):self.curve=slots
    async def async_read_config(self):
        payload=bytes(32)+bytes(c for slot in self.curve for c in slot)
        frame=bytearray(protocol.build_frame(protocol.CMD_READ_CONFIG,payload));frame[0]=protocol.RESPONSE_HEADER;return bytes(frame)
class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):Store.saved={};timers.clear();clock.now=1000
    def make(self):
        tasks=[]
        def create(coro):task=asyncio.create_task(coro);tasks.append(task);return task
        c=Coord(SimpleNamespace(async_create_task=create),FakeClient(),'test');return c,tasks
    async def test_deadline_survives_restart_and_expires(self):
        c,tasks=self.make();await c.async_feeding_set(True);self.assertEqual(c._feeding_deadline,1600)
        await c.async_shutdown();clock.now=1200
        other,tasks=self.make();await other.async_restore_feeding();self.assertTrue(other.feeding_on);self.assertEqual(other._feeding_deadline,1600);self.assertEqual(timers[-1][0],400)
        clock.now=1700;other._feeding_timeout(None);await asyncio.gather(*tasks)
        self.assertFalse(other.feeding_on);self.assertFalse(Store.saved[other._feeding_store.key]['recovery_pending'])
    async def test_unload_cancels_and_late_callback_is_inert(self):
        c,tasks=self.make();await c.async_feeding_set(True);cancel=c._feeding_unsub
        await c.async_shutdown();cancel.assert_called_once();c._feeding_timeout(None);self.assertFalse(tasks)
    async def test_expired_deadline_schedules_immediate_recovery(self):
        c,tasks=self.make();await c.async_feeding_set(True);clock.now=1700
        other,_=self.make();await other.async_restore_feeding();self.assertEqual(timers[-1][0],0)
    async def test_failed_restore_retains_obligation(self):
        c,_=self.make();await c.async_feeding_set(True)
        c.client.async_turn_on.side_effect=OSError('closed')
        with self.assertRaises(OSError):await c.async_feeding_set(False)
        self.assertTrue(Store.saved[c._feeding_store.key]['recovery_pending'])
        other,_=self.make();await other.async_restore_feeding();other.client.async_turn_on.assert_awaited()
    async def test_old_effect_cannot_override_new_off(self):
        c,_=self.make();generation=c._generation
        await c.async_user_off();await c._finish_effect(generation,None,0)
        c.client.async_turn_on.assert_not_awaited();c.client.async_turn_off.assert_awaited_once()
        with self.assertRaises(ctx['_EffectInterrupted']):await c._effect_set_brightness((100,)*4,generation)
    async def test_feeding_takes_priority_then_returns_to_viewing(self):
        c,_=self.make();await c.async_feeding_set(True);await c.async_viewing_set(True)
        self.assertEqual(c.channels,[20]*4);await c.async_feeding_set(False)
        self.assertEqual(c.active_mode,'viewing');self.assertEqual(c.channels,[90,50,60,25])
    async def test_off_survives_feeding_end_and_restart(self):
        c,_=self.make();await c.async_feeding_set(True);await c.async_user_off();await c.async_feeding_set(False)
        c.client.async_turn_on.assert_not_awaited()
        other,_=self.make();await other.async_restore_feeding();self.assertEqual(other.active_mode,'off')
    async def test_preset_replaces_overlay_baseline(self):
        c,_=self.make();c.schedule=[(80,)*4]*5
        await c.async_apply_acclimation(50);await c.async_write_schedule([(30,)*4]*5,540,[60]*5)
        self.assertEqual(c.client.curve,[(15,)*4]*5)
        await c.async_apply_acclimation(100);self.assertEqual(c.client.curve,[(30,)*4]*5)
    async def test_failed_new_preset_preserves_pending_and_old_base(self):
        c,_=self.make();c.schedule=[(80,)*4]*5;await c.async_apply_acclimation(50);c.client.fail=True
        with self.assertRaises(OSError):await c.async_write_schedule([(30,)*4]*5,540,[60]*5)
        other,_=self.make();await other._load_acclimation_base();self.assertEqual(other._acclimation_base,[(80,)*4]*5)
        with self.assertRaises(RuntimeError):await other.async_apply_acclimation(100)
        other.acclimation_scale=50;await other.async_write_schedule([(30,)*4]*5,540,[60]*5);await other.async_apply_acclimation(100)
        self.assertEqual(other.client.curve,[(30,)*4]*5)
    async def test_options_read_failure_sends_nothing(self):
        for method in ['async_set_coral','async_set_auto_cloud']:
            with self.subTest(method=method):
                c=Client(None,'test',8855,protocol.DEFAULT_DEVICE_CODE);c.async_read_options=AsyncMock(side_effect=OSError('read failed'));c._request=AsyncMock()
                with self.assertRaises(OSError):await getattr(c,method)(True)
                c._request.assert_not_awaited()
    async def test_options_edits_serialize_and_preserve_other_bits(self):
        c=Client(None,'test',8855,protocol.DEFAULT_DEVICE_CODE);state=[0,0,0]
        async def read():await asyncio.sleep(0);return SimpleNamespace(auto_cloud=state[0],phase=state[1],coral=state[2])
        async def write(frame,**kwargs):await asyncio.sleep(0);state[:]=frame[8:11]
        c.async_read_options=read;c._request=write
        await asyncio.gather(c.async_set_coral(True),c.async_set_auto_cloud(True))
        self.assertEqual(state,[1,0,1])

    async def test_restart_restores_saved_scale_before_new_preset(self):
        c,_=self.make();c.schedule=[(80,)*4]*5
        await c.async_apply_acclimation(50)
        other,_=self.make();await other.async_write_schedule([(30,)*4]*5,540,[60]*5)
        self.assertEqual(other.client.curve,[(15,)*4]*5)
        await other.async_apply_acclimation(100)
        self.assertEqual(other.client.curve,[(30,)*4]*5)
    async def test_schedule_transport_never_resumes_output_by_itself(self):
        c=Client(None,'test',8855,protocol.DEFAULT_DEVICE_CODE);c._request=AsyncMock()
        await c.async_write_schedule([(30,)*4]*5,540,[60]*5)
        await c.async_write_brightness([(15,)*4]*5)
        self.assertFalse(any(call.args[0][7]==protocol.CMD_START for call in c._request.await_args_list))
    async def test_pending_off_retries_after_restart(self):
        c,_=self.make();c.client.async_turn_off.side_effect=OSError('offline')
        with self.assertRaises(OSError):await c.async_user_off()
        self.assertTrue(Store.saved[c._feeding_store.key]['recovery_pending'])
        other,_=self.make();await other.async_restore_feeding()
        other.client.async_turn_off.assert_awaited_once()
        other.client.async_turn_on.assert_not_awaited()

class HeadroomTests(unittest.IsolatedAsyncioTestCase):
    setUp=RecoveryTests.setUp
    make=RecoveryTests.make
    async def test_model200_and_baseline_dependent_gain(self):
        c,_=self.make();c.client.curve=[(160,100,20,0)]*5
        await c.async_apply_acclimation(125)
        self.assertEqual(c.client.curve,[(200,125,25,0)]*5)
        self.assertEqual(c.max_schedule_gain,125)
        before=dict(Store.saved)
        with self.assertRaises(RuntimeError):await c.async_apply_acclimation(126)
        self.assertEqual(Store.saved,before)
        await c.async_apply_acclimation(100)
        self.assertEqual(c.client.curve,[(160,100,20,0)]*5)
    async def test_external_app_edit_refuses_all_writes_including_restore(self):
        c,_=self.make();await c.async_apply_acclimation(50)
        restored=[(20,100,80,75)]*5;c.client.curve=restored
        c.client.async_write_brightness=AsyncMock();c.client.async_turn_on.reset_mock()
        for value in [40,100]:
            with self.assertRaisesRegex(RuntimeError,'external schedule change'):await c.async_apply_acclimation(value)
        c.client.async_write_brightness.assert_not_awaited();c.client.async_turn_on.assert_not_awaited()
        self.assertTrue(c.schedule_conflict)
        with self.assertRaises(RuntimeError):await c.async_adopt_current_schedule(False)
        await c.async_adopt_current_schedule(True)
        self.assertEqual(c.acclimation_scale,100);self.assertFalse(c.schedule_conflict)
        self.assertEqual(c.client.curve,restored)
        self.assertEqual(len(Store.saved[c._acclimation_store.key+'.history']['revisions']),1)
        c.client.async_write_brightness.assert_not_awaited();c.client.async_turn_on.assert_not_awaited()
    async def test_missing_unknown_and_zero_do_not_offer_boost(self):
        c,_=self.make();self.assertEqual(c.max_schedule_gain,100)
        c.schedule=[(0,)*4]*5;self.assertEqual(c.max_schedule_gain,100)
        c.schedule=[(201,)*4]*5;self.assertEqual(c.max_schedule_gain,100)
    async def test_read_failure_never_writes(self):
        c,_=self.make();c.client.async_read_config=AsyncMock(side_effect=OSError('offline'));c.client.async_write_brightness=AsyncMock()
        with self.assertRaises(OSError):await c.async_apply_acclimation(50)
        c.client.async_write_brightness.assert_not_awaited();self.assertEqual(Store.saved,{})
