"""Run actual storm v2 templates/actions locally, with no network/transport."""
from pathlib import Path
import math,unittest,yaml
from types import SimpleNamespace
from jinja2 import Environment,StrictUndefined
ROOT=Path(__file__).resolve().parents[1]
class I(str):pass
class L(yaml.SafeLoader):pass
L.add_constructor('!input',lambda l,n:I(l.construct_scalar(n)))
BP=yaml.load((ROOT/'blueprints/automation/zetlight_led/whole_tank_storm_gain.yaml').read_text(),Loader=L)
ENV=Environment(undefined=StrictUndefined)
IDS=dict(weather_entity='weather.home',lightning_button='button.flash',pump_fan='fan.wave',pump_wave_mode='select.wave',pump_run_mode='select.run',light_entity='light.coral',feeding_switch='switch.feed',maintenance_toggle='input_boolean.maint',maintenance_restore_marker='input_boolean.restore',pump_flow_mode='sensor.flow',storm_owner='input_boolean.owner',pump_schedule='sensor.schedule',pump_tidal_gain='number.gain')
def is_number(x):
 try:return math.isfinite(float(x))
 except(TypeError,ValueError):return False
class Stop(Exception):pass
class Sim:
 def __init__(self,states=None,inputs=None,mode='schedule',hook=None,wait_hook=None,fail=None):
  self.inputs={k:v['default']for k,v in BP['blueprint']['input'].items()if'default'in v};self.inputs.update(IDS);self.inputs.update(clock_confirmed=True);self.inputs.update(inputs or {})
  self.states={'weather.home':'lightning','fan.wave':'on','select.wave':'sine','select.run':'tide','light.coral':'on','switch.feed':'off','input_boolean.maint':'off','input_boolean.restore':'off','sensor.flow':'sine','input_boolean.owner':'off'}
  self.states.update({'sensor.schedule':'24','number.gain':'130'});self.states.update(states or {});self.hour=12;self.baseline=[60]*24;self.schedule=[dict(hour=h,power=78,mode='sine')for h in range(24)];self.pending=False;self.mode=mode;self.calls=[];self.waits=[];self.hook=hook;self.wait_hook=wait_hook;self.fail=fail;self.stopped=False
 def attr(self,e,k):
  return {('light.coral','active_mode'):self.mode,('sensor.schedule','schedule'):self.schedule,('number.gain','baseline_powers'):self.baseline,('number.gain','recovery_required'):self.pending}.get((e,k))
 def val(self,x):
  if isinstance(x,I):return self.inputs[x]
  if isinstance(x,dict):return{k:self.val(v)for k,v in x.items()}
  if isinstance(x,list):return[self.val(v)for v in x]
  if isinstance(x,str)and('{{'in x or'{%'in x):return ENV.from_string(x).render(**self.ctx).strip()
  return x
 def yes(self,x):return self.val(x)=='True'
 def run(self):
  self.ctx={'states':lambda e:self.states.get(e,'unknown'),'is_state':lambda e,v:self.states.get(e,'unknown')==v,'state_attr':self.attr,'now':lambda:SimpleNamespace(hour=self.hour),'is_number':is_number}
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
    elif svc=='gts_wavepump.storm_gain':self.states['select.run']='manual'
    elif svc=='select.select_option':
     self.states[e]=data['option']
     if e=='select.wave':self.states['select.run']='manual';self.states['sensor.flow']=data['option']
    if self.hook:self.hook(self,svc)
   else:raise AssertionError(r)
class StormGainTests(unittest.TestCase):
 def test_peak_gap_and_restore(self):
  s=Sim();s.run()
  calls=[d for svc,e,d in s.calls if svc=='gts_wavepump.storm_gain']
  self.assertEqual([float(d['gain'])for d in calls],[150,130]);self.assertEqual([d['wave_mode']for d in calls],['daily','daily'])
  self.assertEqual([d['expected_run_mode']for d in calls],['tide','manual'])
  # Exit detected while waiting aborts the current run. Weather trigger reruns restoration.
  s.calls=[];s.run();self.assertEqual(s.states['select.run'],'tide');self.assertEqual(s.states['input_boolean.owner'],'off')
  self.assertFalse(any(svc in ['fan.set_percentage','fan.turn_on','light.turn_on']for svc,e,d in s.calls))
 def test_weather_gain_sets_gap_floor_without_compounding(self):
  s=Sim({'number.gain':'140'});s.run();self.assertEqual([float(d['gain'])for svc,e,d in s.calls if svc=='gts_wavepump.storm_gain'],[]) # weather output84 exceeds raw cap80
  s=Sim({'number.gain':'140'},inputs={'power_ceiling':90});s.run();self.assertEqual([float(d['gain'])for svc,e,d in s.calls if svc=='gts_wavepump.storm_gain'],[150,140])
 def test_zero_night_missing_and_invalid_values(self):
  for case in ['zero','missing','pending','incomplete','invalid','clock','cap','attenuation','above_peak','unknown_gain','unknown_schedule','mode','missing_field','non_mapping']:
   s=Sim()
   if case=='zero':s.baseline[12]=0
   elif case=='missing':s.baseline=None
   elif case=='pending':s.pending=True
   elif case=='incomplete':s.schedule=s.schedule[:23]
   elif case=='invalid':s.baseline[0]=True
   elif case=='clock':s.inputs['clock_confirmed']=False
   elif case=='cap':s.inputs['power_ceiling']=70
   elif case=='attenuation':s.states['number.gain']='50'
   elif case=='above_peak':s.states['number.gain']='160'
   elif case=='unknown_gain':s.states['number.gain']='unknown'
   elif case=='unknown_schedule':s.states['sensor.schedule']='unavailable'
   elif case=='mode':s.schedule[12]['mode']='off'
   elif case=='missing_field':s.schedule[1].pop('power')
   elif case=='non_mapping':s.schedule[1]=None
   with self.subTest(case=case):self.assertEqual(s.run(),[])
  s=Sim();s.baseline=[6]*24;s.run();self.assertTrue(any(svc=='gts_wavepump.storm_gain'for svc,e,d in s.calls))
 def test_gain100_can_use_current_unscaled_schedule(self):
  s=Sim({'number.gain':'100'});s.baseline=None;s.schedule=[dict(hour=h,power=40,mode='sine')for h in range(24)];s.run();self.assertTrue(any(svc=='gts_wavepump.storm_gain'for svc,e,d in s.calls))
 def test_owned_invalid_or_zero_hour_restores_without_starting_pump(self):
  for case in ['weather','zero','cap','clock','missing']:
   s=Sim({'select.run':'manual','input_boolean.owner':'on'})
   if case=='weather':s.states['weather.home']='sunny'
   if case=='zero':s.baseline[12]=0
   if case=='cap':s.inputs['power_ceiling']=50
   if case=='clock':s.inputs['clock_confirmed']=False
   if case=='missing':s.baseline=None
   s.run();self.assertEqual(s.calls,[('select.select_option','select.run',{'option':'tide'}),('input_boolean.turn_off','input_boolean.owner',{})])
  s=Sim({'weather.home':'sunny','fan.wave':'off','select.run':'tide','input_boolean.owner':'on'});s.run();self.assertEqual(s.calls,[('input_boolean.turn_off','input_boolean.owner',{})])
 def test_interlocks_and_unowned_manual_never_operate(self):
  for changes in [{'select.run':'manual'},{'fan.wave':'off'},{'sensor.flow':'feed'},{'sensor.flow':'unknown'},{'switch.feed':'on'},{'input_boolean.maint':'on'},{'input_boolean.restore':'on'},{'weather.home':'unknown'}]:
   self.assertEqual(Sim(changes).run(),[])
  for changes in [{'fan.wave':'off'},{'sensor.flow':'feed'},{'switch.feed':'on'},{'input_boolean.maint':'on'}]:
   s=Sim(dict({'weather.home':'sunny','input_boolean.owner':'on','select.run':'manual'},**changes));self.assertEqual(s.run(),[])
 def test_feed_during_flash_and_maintenance_during_wait(self):
  def hook(s,svc):
   if svc=='button.press':s.states['switch.feed']='on'
  s=Sim(hook=hook);s.run();self.assertFalse(any(svc=='gts_wavepump.storm_gain'for svc,e,d in s.calls))
  def interrupt(s,n):s.states['input_boolean.maint']='on'
  s=Sim(wait_hook=interrupt);s.run();self.assertEqual(len([svc for svc,e,d in s.calls if svc=='gts_wavepump.storm_gain']),1);self.assertEqual(s.states['input_boolean.owner'],'on')
 def test_hour_boundary_rechecks_zero_and_restore(self):
  def midnight(s,n):s.hour=0
  s=Sim(wait_hook=midnight);s.baseline[0]=0;s.run();self.assertEqual(len([svc for svc,e,d in s.calls if svc=='gts_wavepump.storm_gain']),1)
  s.calls=[];s.run();self.assertEqual(s.states['select.run'],'tide');self.assertEqual(s.states['input_boolean.owner'],'off')
  self.assertTrue(any(t.get('platform')=='time_pattern'for t in BP['trigger']))
 def test_failed_command_retains_marker_and_stops_sequence(self):
  s=Sim(fail='gts_wavepump.storm_gain');s.run();self.assertEqual(s.waits,[]);self.assertEqual(s.states['input_boolean.owner'],'on')
 def test_defaults_are_not_authorization_or_safety_measurement(self):
  self.assertFalse(BP['blueprint']['input']['clock_confirmed']['default'])
  self.assertNotIn('pump_wave_mode',BP['blueprint']['input'])
if __name__=='__main__':unittest.main()
