"""Run actual storm v2 templates/actions locally, with no network/transport."""
from pathlib import Path
import math,unittest,yaml
from jinja2 import Environment,StrictUndefined
ROOT=Path(__file__).resolve().parents[1]
class I(str):pass
class L(yaml.SafeLoader):pass
L.add_constructor('!input',lambda l,n:I(l.construct_scalar(n)))
BP=yaml.load((ROOT/'blueprints/automation/zetlight_led/whole_tank_storm_v2.yaml').read_text(),Loader=L)
ENV=Environment(undefined=StrictUndefined)
IDS=dict(weather_entity='weather.home',lightning_button='button.flash',pump_fan='fan.wave',pump_wave_mode='select.wave',pump_run_mode='select.run',light_entity='light.coral',feeding_switch='switch.feed',maintenance_toggle='input_boolean.maint',maintenance_restore_marker='input_boolean.restore',pump_flow_mode='sensor.flow',storm_owner='input_boolean.owner')
def is_number(x):
 try:return math.isfinite(float(x))
 except(TypeError,ValueError):return False
class Stop(Exception):pass
class Sim:
 def __init__(self,states=None,inputs=None,mode='schedule',hook=None,wait_hook=None,fail=None):
  self.inputs={k:v['default']for k,v in BP['blueprint']['input'].items()if'default'in v};self.inputs.update(IDS);self.inputs.update(inputs or {})
  self.states={'weather.home':'lightning','fan.wave':'on','select.wave':'sine','select.run':'tide','light.coral':'on','switch.feed':'off','input_boolean.maint':'off','input_boolean.restore':'off','sensor.flow':'sine','input_boolean.owner':'off'}
  self.states.update(states or {});self.mode=mode;self.calls=[];self.waits=[];self.hook=hook;self.wait_hook=wait_hook;self.fail=fail;self.stopped=False
 def val(self,x):
  if isinstance(x,I):return self.inputs[x]
  if isinstance(x,dict):return{k:self.val(v)for k,v in x.items()}
  if isinstance(x,list):return[self.val(v)for v in x]
  if isinstance(x,str)and('{{'in x or'{%'in x):return ENV.from_string(x).render(**self.ctx).strip()
  return x
 def yes(self,x):return self.val(x)=='True'
 def run(self):
  self.ctx={'states':lambda e:self.states.get(e,'unknown'),'is_state':lambda e,v:self.states.get(e,'unknown')==v,'state_attr':lambda e,k:self.mode if(e,k)==('light.coral','active_mode')else None,'is_number':is_number}
  for k,v in BP['variables'].items():self.ctx[k]=self.val(v)
  try:self.exec(BP['action'])
  except Stop:self.stopped=True
  return self.calls
 def exec(self,seq):
  for r in seq:
   if'condition'in r:
    if not self.yes(r['value_template']):raise Stop()
   elif'if'in r:self.exec(r.get('then',[])if self.yes(r['if'])else r.get('else',[]))
   elif'choose'in r:
    for b in r['choose']:
     if self.yes(b['conditions']):self.exec(b['sequence']);break
   elif'repeat'in r:
    count=0
    while all(self.yes(x)for x in r['repeat']['while']):
     count+=1
     if count>2:raise AssertionError('test must end storm within two simulated bursts')
     self.exec(r['repeat']['sequence'])
   elif'wait_template'in r:
    self.waits.append(int(self.val(r['timeout']['seconds'])))
    if self.wait_hook:self.wait_hook(self,len(self.waits))
    elif len(self.waits)==2:self.states['weather.home']='sunny'
   elif'service'in r:
    svc=r['service'];e=self.val(r['target']['entity_id']);data=self.val(r.get('data',{}));self.calls.append((svc,e,data))
    if self.fail==svc:raise Stop()
    if svc=='input_boolean.turn_on':self.states[e]='on'
    elif svc=='input_boolean.turn_off':self.states[e]='off'
    elif svc=='select.select_option':
     self.states[e]=data['option']
     if e=='select.wave':self.states['select.run']='manual';self.states['sensor.flow']=data['option']
    if self.hook:self.hook(self,svc)
   else:raise AssertionError(r)
class StormTests(unittest.TestCase):
 def test_burst_gap_and_clear_restore_owned_tide(self):
  s=Sim();s.run() # wait-triggered clear aborts one run; state trigger starts restore run
  self.assertEqual([int(d['percentage'])for svc,e,d in s.calls if svc=='fan.set_percentage'],[65,45])
  self.assertTrue(8<=s.waits[0]<=12);self.assertTrue(90<=s.waits[1]<=180)
  self.assertEqual(s.calls[-2:],[('select.select_option','select.run',{'option':'tide'}),('input_boolean.turn_off','input_boolean.owner',{})])
  s.calls=[];self.assertEqual(s.run(),[])
 def test_no_weather_or_unowned_manual_is_not_taken_over(self):
  for changes in [{'weather.home':'sunny'},{'weather.home':'rainy'},{'weather.home':'pouring'},{'weather.home':'unknown'},{'select.run':'manual'},{'select.run':'unavailable'}]:
   self.assertEqual(Sim(changes).run(),[])
 def test_modes_missing_and_power_off_never_start(self):
  for e in ['switch.feed','input_boolean.maint','input_boolean.restore']:
   for value in ['on','unknown','unavailable']:self.assertEqual(Sim({e:value}).run(),[])
  for changes in [{'fan.wave':'off'},{'fan.wave':'unavailable'},{'sensor.flow':'feed'},{'sensor.flow':'unknown'},{'input_boolean.owner':'unknown'}]:self.assertEqual(Sim(changes).run(),[])
 def test_closed_manual_or_viewing_light_never_flashes(self):
  for states,mode in [({'light.coral':'off'},'schedule'),({},'manual'),({},'viewing')]:
   s=Sim(states,mode=mode);s.run();self.assertFalse(any(c[0]=='button.press'for c in s.calls));self.assertTrue(any(c[0]=='fan.set_percentage'for c in s.calls))
 def test_owned_clear_or_missing_weather_restores_once(self):
  for weather in ['sunny','unknown','unavailable']:
   s=Sim({'weather.home':weather,'input_boolean.owner':'on','select.run':'manual'});s.run()
   self.assertEqual(s.states['select.run'],'tide');self.assertEqual(s.states['input_boolean.owner'],'off')
   s.calls=[];self.assertEqual(s.run(),[])
 def test_owned_restore_waits_for_mode_power_and_flow(self):
  for changes in [{'switch.feed':'on'},{'input_boolean.maint':'on'},{'input_boolean.restore':'on'},{'fan.wave':'off'},{'sensor.flow':'feed'},{'select.run':'unavailable'}]:
   s=Sim(dict({'weather.home':'sunny','input_boolean.owner':'on','select.run':'manual'},**changes));self.assertEqual(s.run(),[]);self.assertEqual(s.states['input_boolean.owner'],'on')
 def test_feed_or_maintenance_during_flash_blocks_pump(self):
  for e,v in [('switch.feed','on'),('input_boolean.maint','on'),('input_boolean.restore','on'),('fan.wave','off'),('sensor.flow','feed')]:
   def hook(s,svc):
    if svc=='button.press':s.states[e]=v
   s=Sim(hook=hook);s.run();self.assertFalse(any(c[0]in['fan.set_percentage','select.select_option']for c in s.calls))
 def test_interrupted_burst_has_no_calm_or_restore_command(self):
  def interrupt(s,n):s.states['input_boolean.maint']='on'
  s=Sim(wait_hook=interrupt);s.run();self.assertEqual([int(d['percentage'])for svc,e,d in s.calls if svc=='fan.set_percentage'],[65]);self.assertEqual(s.states['input_boolean.owner'],'on')
 def test_invalid_ranges_and_cap_are_rejected(self):
  for inputs in [{'surge_percentage':95},{'calm_percentage':70},{'burst_min':20,'burst_max':10},{'gap_min':200,'gap_max':100},{'surge_percentage':'nan'}]:
   self.assertEqual(Sim(inputs=inputs).run(),[])
 def test_failed_service_does_not_clear_ownership_or_run_next_action(self):
  s=Sim(fail='fan.set_percentage');s.run();self.assertEqual(s.states['input_boolean.owner'],'on');self.assertEqual(s.waits,[])
  s=Sim({'weather.home':'sunny','select.run':'manual','input_boolean.owner':'on'},fail='select.select_option');s.run();self.assertEqual(s.states['input_boolean.owner'],'on')
 def test_no_power_on_service_and_guard_conditions_around_effects(self):
  text=(ROOT/'blueprints/automation/zetlight_led/whole_tank_storm_v2.yaml').read_text()
  self.assertNotIn('service: fan.turn_on',text);self.assertNotIn('service: light.turn_on',text)
  self.assertEqual(BP['mode'],'restart');self.assertIn('storm_owner',BP['blueprint']['input'])
if __name__=='__main__':unittest.main()
