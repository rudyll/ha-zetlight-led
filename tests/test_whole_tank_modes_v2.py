"""Execute actual blueprint branches with fake states/services; no HA connection."""
import copy
from pathlib import Path
import unittest
import yaml
from jinja2 import Environment, StrictUndefined
ROOT=Path(__file__).resolve().parents[1]
class Input(str): pass
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!input',lambda l,n:Input(l.construct_scalar(n)))
BP=yaml.load((ROOT/'blueprints/automation/zetlight_led/whole_tank_modes_v2.yaml').read_text(),Loader=Loader)
ENV=Environment(undefined=StrictUndefined)
INPUTS=dict(feeding_switch='switch.feed',maintenance_toggle='input_boolean.maint',
 light_restore_marker='input_boolean.marker',light_entity='light.coral',pump_fan='fan.wave',
 pump_feed_button='button.feed',pump_flow_mode='sensor.flow',skimmer_supply='switch.skimmer',return_supply='switch.return',skimmer_settle_seconds=30)
class Sim:
 def __init__(self,states=None,mode='schedule',fail=(),inputs=None,delay_hook=None):
  self.inputs=dict(INPUTS,**(inputs or {}));self.states={'switch.feed':'off','input_boolean.maint':'off',
   'input_boolean.marker':'off','light.coral':'on','fan.wave':'on','button.feed':'unknown',
   'sensor.flow':'sine','switch.skimmer':'on','switch.return':'on'}
  self.states.update(states or {});self.attrs={'active_mode':mode,'command_error':None};self.calls=[];self.fail=set(fail);self.delays=[];self.delay_hook=delay_hook;self.stopped=None
 def val(self,x):
  if isinstance(x,Input):return self.inputs[x]
  if isinstance(x,str) and ('{{' in x or '{%' in x):return ENV.from_string(x).render(**self.ctx).strip()
  return x
 def yes(self,x):return self.val(x)=='True'
 def run(self,trigger='mode'):
  self.ctx={'trigger':{'id':trigger},'states':lambda e:self.states.get(e,'unknown'),
   'is_state':lambda e,v:self.states.get(e,'unknown')==v,
   'state_attr':lambda e,k:self.attrs.get(k) if e=='light.coral' else None}
  self.ctx.update({k:self.val(v) for k,v in BP['variables'].items()})
  if self.yes(BP['condition'][0]['value_template']):
   try:self.exec(BP['action'])
   except RuntimeError as e:self.stopped=str(e)
  return self.calls
 def exec(self,seq):
  for row in seq:
   if 'wait_template' in row:
    if not self.yes(row['wait_template']) and not row.get('continue_on_timeout',False):return
   elif 'stop' in row:raise RuntimeError(row['stop'])
   elif 'delay' in row:
    self.delays.append(self.val(row['delay']['seconds']))
    if self.delay_hook:self.delay_hook(self)
   elif 'if' in row:self.exec(row.get('then',[]) if self.yes(row['if']) else row.get('else',[]))
   elif 'choose' in row:
    for branch in row['choose']:
     if self.yes(branch['conditions']):self.exec(branch['sequence']);break
    else:self.exec(row.get('default',[]))
   elif 'action' in row:
    service=row['action'];entity=self.val(row['target']['entity_id']);self.calls.append((service,entity))
    if (service,entity) in self.fail:
     if entity=='light.coral':self.attrs['command_error']='unconfirmed'
     if not row.get('continue_on_error'):raise RuntimeError('service failed')
     continue
    if service=='button.press':self.states['sensor.flow']='feed';self.states['fan.wave']='on'
    else:
     self.states[entity]='on' if service.endswith('turn_on') else 'off'
     if entity=='light.coral':self.attrs.update(active_mode=('feeding' if self.states['switch.feed']=='on' else 'schedule') if service.endswith('turn_on') else 'off',command_error=None)
     if entity=='fan.wave' and service.endswith('turn_on'):self.states['sensor.flow']='sine'

class ModesTests(unittest.TestCase):
 def test_maintenance_order_and_marker_before_off(self):
  s=Sim({'input_boolean.maint':'on'});calls=s.run()
  self.assertEqual(calls,[('input_boolean.turn_on','input_boolean.marker'),('fan.turn_off','fan.wave'),('light.turn_off','light.coral'),('switch.turn_off','switch.skimmer'),('switch.turn_off','switch.return')])
  self.assertEqual(s.states['input_boolean.marker'],'on')
 def test_end_restores_return_skimmer_wave_then_owned_light(self):
  s=Sim({'input_boolean.marker':'on','fan.wave':'off','switch.skimmer':'off','switch.return':'off','light.coral':'off'},mode='off')
  self.assertEqual(s.run(),[('switch.turn_on','switch.return'),('switch.turn_on','switch.skimmer'),('fan.turn_on','fan.wave'),('light.turn_on','light.coral'),('input_boolean.turn_off','input_boolean.marker')])
 def test_maintenance_wins_over_feed_even_if_feed_ends(self):
  s=Sim({'input_boolean.maint':'on','switch.feed':'on'});s.run();s.calls=[];s.states['switch.feed']='off';s.run()
  self.assertEqual(s.calls,[])
  for e in ['fan.wave','switch.skimmer','switch.return','light.coral']:self.assertEqual(s.states[e],'off')
 def test_maintenance_end_while_feeding_does_not_restore_supplies(self):
  s=Sim({'switch.feed':'on','input_boolean.marker':'on','fan.wave':'off','switch.skimmer':'off','switch.return':'off','light.coral':'off'},mode='off');s.run()
  self.assertEqual(s.states['switch.skimmer'],'off');self.assertEqual(s.states['switch.return'],'off')
  self.assertIn(('button.press','button.feed'),s.calls);self.assertNotIn(('fan.turn_on','fan.wave'),s.calls)
  self.assertEqual(s.attrs['active_mode'],'feeding')
 def test_unknown_modes_do_not_restore_but_maintenance_can_stop(self):
  for key in ['switch.feed','input_boolean.maint']:
   s=Sim({key:'unavailable'});self.assertEqual(s.run(),[])
  s=Sim({'switch.feed':'unavailable','input_boolean.maint':'on'});s.run();self.assertEqual(s.states['switch.return'],'off')
 def test_initially_off_light_stays_off_after_maintenance(self):
  s=Sim({'input_boolean.maint':'on','light.coral':'off'},mode='off');s.run();self.assertNotIn(('input_boolean.turn_on','input_boolean.marker'),s.calls)
  s.states['input_boolean.maint']='off';s.calls=[];s.run();self.assertNotIn(('light.turn_on','light.coral'),s.calls)
 def test_one_failed_stop_does_not_block_other_stops(self):
  s=Sim({'input_boolean.maint':'on'},fail=[('fan.turn_off','fan.wave')]);s.run()
  self.assertEqual(s.states['switch.return'],'off');self.assertEqual(s.states['light.coral'],'off')
 def test_failed_light_restore_keeps_marker_for_recovery(self):
  s=Sim({'input_boolean.marker':'on','light.coral':'off'},mode='off',fail=[('light.turn_on','light.coral')]);s.run()
  self.assertEqual(s.states['input_boolean.marker'],'on')
  s.fail=set();s.run(trigger='reconcile');self.assertEqual(s.states['input_boolean.marker'],'off')
 def test_native_feed_is_preserved_and_not_repressed_if_active(self):
  s=Sim({'switch.feed':'on'});s.run();self.assertEqual(s.states['sensor.flow'],'feed');self.assertIn(('button.press','button.feed'),s.calls)
  s.calls=[];s.run(trigger='reconcile');self.assertNotIn(('button.press','button.feed'),s.calls)
  s.states['switch.feed']='off';s.calls=[];s.run();self.assertIn(('fan.turn_on','fan.wave'),s.calls);self.assertEqual(s.states['sensor.flow'],'sine')
 def test_return_failure_never_starts_skimmer(self):
  s=Sim({'switch.return':'off','switch.skimmer':'off'},fail=[('switch.turn_on','switch.return')]);s.run();self.assertNotIn(('switch.turn_on','switch.skimmer'),s.calls);self.assertIsNotNone(s.stopped)
 def test_skimmer_stop_failure_keeps_return_on(self):
  s=Sim({'input_boolean.maint':'on'},fail=[('switch.turn_off','switch.skimmer')]);s.run();self.assertNotIn(('switch.turn_off','switch.return'),s.calls);self.assertEqual(s.states['switch.return'],'on');self.assertIsNotNone(s.stopped)
 def test_exact_30_second_settle_and_mode_or_power_change_cancels_skimmer(self):
  s=Sim({'switch.return':'off','switch.skimmer':'off'});s.run();self.assertEqual(s.delays,[30]);self.assertIn(('switch.turn_on','switch.skimmer'),s.calls)
  for target,value in [('switch.feed','on'),('input_boolean.maint','on'),('switch.return','off')]:
   s=Sim({'switch.return':'off','switch.skimmer':'off'},delay_hook=lambda sim,t=target,v=value:sim.states.update({t:v}));s.run();self.assertNotIn(('switch.turn_on','switch.skimmer'),s.calls);self.assertIsNotNone(s.stopped)
 def test_missing_optional_targets_never_called(self):
  s=Sim({'input_boolean.maint':'on'},inputs={k:[] for k in ['pump_fan','pump_feed_button','pump_flow_mode','skimmer_supply','return_supply']});s.run()
  self.assertTrue(all(e in ['input_boolean.marker','light.coral'] for _,e in s.calls))
 def test_partial_optional_native_feed_without_fan_is_safe(self):
  s=Sim({'switch.feed':'on','sensor.flow':'feed'},inputs={'pump_fan':[]});s.run();self.assertNotIn(('button.press','button.feed'),s.calls)
 def test_failed_marker_does_not_block_maintenance_stops(self):
  s=Sim({'input_boolean.maint':'on'},fail=[('input_boolean.turn_on','input_boolean.marker')]);s.run();self.assertEqual(s.states['switch.return'],'off');self.assertEqual(s.states['light.coral'],'off')
 def test_idle_reconcile_no_actuator_command_and_lamp_change_is_ignored(self):
  self.assertEqual(Sim().run(trigger='reconcile'),[])
  self.assertEqual(Sim({'switch.feed':'on'}).run(trigger='lamp_change'),[])
 def test_active_mode_overrides_stale_off_state(self):
  s=Sim({'input_boolean.maint':'on','light.coral':'off'},mode='viewing');s.run();self.assertIn(('light.turn_off','light.coral'),s.calls)

if __name__=='__main__':unittest.main()
