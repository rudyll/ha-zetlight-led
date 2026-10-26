"""Exercise the blueprint's actual templates and guarded action sequence offline."""
import math
from pathlib import Path
import unittest
import yaml
from jinja2 import Environment, StrictUndefined
class Input(str): pass
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!input',lambda l,n:Input(l.construct_scalar(n)))
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'blueprints/automation/zetlight_led/viewing_sun.yaml'
BP=yaml.load(PATH.read_text(),Loader=Loader)
ENV=Environment(undefined=StrictUndefined)
def numeric(v):
 try:return math.isfinite(float(v))
 except (TypeError,ValueError):return False
class Sim:
 def __init__(self,sun='above_horizon',view='off',mode='schedule',states=None,inputs=None,fail=None,hook=None):
  self.inputs={k:v['default']for k,v in BP['blueprint']['input'].items()if 'default'in v}
  self.inputs.update({'viewing_switch':'switch.view','light_entity':'light.coral','feeding_switch':'switch.feed','maintenance_toggle':'input_boolean.maint','maintenance_restore_marker':'input_boolean.restore',**{'viewing_'+c:'number.view_'+c for c in 'abcd'}})
  self.inputs.update(inputs or {});self.states={'sun.sun':sun,'switch.view':view,'switch.feed':'off','input_boolean.maint':'off','input_boolean.restore':'off',**{'number.view_'+c:str(v)for c,v in zip('abcd',[90,50,60,24])}};self.states.update(states or {})
  self.mode=mode;self.calls=[];self.fail=fail;self.hook=hook
  self.ctx={'states':lambda e:self.states.get(e,'unknown'),'is_state':lambda e,v:self.states.get(e,'unknown')==v,'state_attr':lambda e,k:self.mode if e=='light.coral'and k=='active_mode'else None,'is_number':numeric}
 def val(self,x):
  if isinstance(x,Input):return self.inputs[x]
  if isinstance(x,str)and('{{'in x or '{%'in x):return ENV.from_string(x).render(**self.ctx).strip()
  return x
 def run(self):
  for k,v in BP['variables'].items():self.ctx[k]=self.val(v)
  for action in BP['action']:
   if 'condition'in action:
    if self.val(action['value_template'])!='True':break
   elif 'variables'in action:
    for k,v in action['variables'].items():self.ctx[k]=self.val(v)
   elif 'if'in action and self.val(action['if'])=='True':
    for a in action['then']:
     assert a['service']=='number.set_value'
     e=self.val(a['target']['entity_id']);v=int(self.val(a['data']['value']));self.calls.append((e,v))
     if e==self.fail:raise RuntimeError('fake service failure')
     self.states[e]=str(v)
     if self.hook:self.hook(self,e)
  return self.calls
class ViewingTests(unittest.TestCase):
 def test_day_and_night_exact_values(self):
  for sun,values in [('above_horizon',[10,10,30,25]),('below_horizon',[5,5,15,12])]:
   with self.subTest(sun=sun):self.assertEqual(Sim(sun).run(),[('number.view_'+c,v)for c,v in zip('abcd',values)])
 def test_active_view_uses_same_profile(self):
  self.assertEqual(Sim('below_horizon',view='on',mode='viewing').run(),[('number.view_'+c,v)for c,v in zip('abcd',[5,5,15,12])])
 def test_same_profile_does_not_write_again(self):
  s=Sim();s.run();s.calls=[];self.assertEqual(s.run(),[])
 def test_sunset_then_sunrise_no_compounding(self):
  s=Sim();s.run();s.states['sun.sun']='below_horizon';s.calls=[];s.run();s.states['sun.sun']='above_horizon';s.calls=[]
  self.assertEqual(s.run(),[('number.view_'+c,v)for c,v in zip('abcd',[10,10,30,25])])
 def test_unknown_sun_and_guards_never_write(self):
  for sun in ['unknown','unavailable','']:
   self.assertEqual(Sim(sun).run(),[])
  for e in ['switch.feed','input_boolean.maint','input_boolean.restore']:
   for value in ['on','unknown','unavailable']:
    with self.subTest(e=e,value=value):self.assertEqual(Sim(states={e:value}).run(),[])
 def test_missing_any_target_skips_entire_profile(self):
  for c in 'abcd':
   for value in ['unknown','unavailable','nan','inf']:
    self.assertEqual(Sim(states={'number.view_'+c:value}).run(),[])
 def test_invalid_or_duplicate_inputs_never_write(self):
  for key in ['day_a','day_b','day_c','day_d','night_scale']:
   for value in [-1,101,'unknown',float('nan')]:
    with self.subTest(key=key,value=value):self.assertEqual(Sim(inputs={key:value}).run(),[])
  self.assertEqual(Sim(inputs={'viewing_b':'number.view_a'}).run(),[])
 def test_power_off_with_view_latched_does_not_send_off_or_on(self):
  self.assertEqual(Sim(view='on',mode='off').run(),[])
 def test_unknown_or_conflicting_modes_do_not_write(self):
  for view,mode in [('unavailable','schedule'),('unknown','schedule'),('on','manual'),('on','feeding'),('off','feeding'),('off',None)]:
   self.assertEqual(Sim(view=view,mode=mode).run(),[])
 def test_guard_changes_between_writes_stop_sequence(self):
  for key in ['switch.feed','input_boolean.maint','input_boolean.restore']:
   s=Sim(hook=lambda s,e,k=key:s.states.update({k:'on'}));self.assertEqual(s.run(),[('number.view_a',10)])
 def test_service_failure_stops_later_channels(self):
  s=Sim(fail='number.view_b')
  with self.assertRaises(RuntimeError):s.run()
  self.assertEqual(s.calls,[('number.view_a',10),('number.view_b',10)])
 def test_zero_night_scale_supported_without_division(self):
  self.assertEqual(Sim('below_horizon',inputs={'night_scale':0}).run(),[('number.view_'+c,0)for c in 'abcd'])
 def test_only_viewing_number_services_and_no_program_write(self):
  self.assertEqual({a['service']for r in BP['action']for a in r.get('then',[])},{'number.set_value'})
  self.assertNotIn('profile_scale',BP['variables'])
 def test_restart_sun_and_view_triggers_present(self):
  ts=BP['trigger'];self.assertTrue(any(t['platform']=='homeassistant'for t in ts));self.assertEqual({t['to']for t in ts if t.get('entity_id')=='sun.sun'},{'above_horizon','below_horizon'})
if __name__=='__main__':unittest.main()
