"""Execute the weather blueprint's actual Jinja/actions with local fake services."""
import math
from pathlib import Path
import unittest
import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
class Input(str): pass
class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!input', lambda loader, node: Input(loader.construct_scalar(node)))
BP = yaml.load((ROOT/'blueprints/automation/zetlight_led/whole_tank_weather_v2.yaml').read_text(), Loader=Loader)
ENV = Environment(undefined=StrictUndefined)
ENTITIES = dict(weather_entity='weather.home', light_entity='light.coral',
 light_dimming='number.light_scale', pump_fan='fan.wave', pump_tidal='number.tidal',
 pump_run_mode='select.run', pump_flow_mode='sensor.flow', feeding_switch='switch.feed',
 maintenance_toggle='input_boolean.maint', maintenance_restore_marker='input_boolean.restore')

def is_number(value):
 try: return math.isfinite(float(value))
 except (ValueError, TypeError): return False

class Sim:
 def __init__(self, weather='sunny', states=None, inputs=None, attrs=None, fail=(), hook=None):
  self.inputs={k:v['default'] for k,v in BP['blueprint']['input'].items() if 'default' in v}
  self.inputs.update(ENTITIES);self.inputs.update(inputs or {})
  self.states={'weather.home':weather,'light.coral':'on','number.light_scale':'100',
   'fan.wave':'on','number.tidal':'100','select.run':'tide','sensor.flow':'sine',
   'switch.feed':'off','input_boolean.maint':'off','input_boolean.restore':'off'}
  self.states.update(states or {});self.attrs={('light.coral','active_mode'):'schedule',('number.tidal','max'):148,('number.tidal','gain_basis'):'app_percent',('number.tidal','recovery_required'):False,('number.light_scale','max'):200,('number.light_scale','gain_basis'):'saved_schedule',('number.light_scale','external_schedule_conflict'):False}
  self.attrs.update(attrs or {});self.calls=[];self.fail=set(fail);self.hook=hook
 def val(self,value):
  if isinstance(value,Input):return self.inputs[value]
  if isinstance(value,dict):return {k:self.val(v) for k,v in value.items()}
  if isinstance(value,list):return [self.val(v) for v in value]
  if isinstance(value,str) and ('{{' in value or '{%' in value):
   return ENV.from_string(value).render(**self.ctx).strip()
  return value
 def run(self):
  self.ctx={'states':lambda e:self.states.get(e,'unknown'),
   'is_state':lambda e,v:self.states.get(e,'unknown')==v,
   'state_attr':lambda e,k:self.attrs.get((e,k)), 'is_number':is_number}
  for k,v in BP['variables'].items():self.ctx[k]=self.val(v)
  self.exec(BP['action']);return self.calls
 def exec(self,steps):
  for row in steps:
   if 'variables' in row:
    for k,v in row['variables'].items():self.ctx[k]=self.val(v)
   elif 'condition' in row:
    if self.val(row['value_template'])!='True':return
   elif 'if' in row:
    self.exec(row.get('then',[]) if self.val(row['if'])=='True' else row.get('else',[]))
   elif 'service' in row:
    entity=self.val(row['target']['entity_id']);value=int(self.val(row['data']['value']))
    self.calls.append((row['service'],entity,value))
    if entity in self.fail:
     if not row.get('continue_on_error'):raise RuntimeError('fake failure')
    else:self.states[entity]=str(value)
    if self.hook:self.hook(self,entity)
   else:raise AssertionError(f'Untested action: {row}')

class WeatherTests(unittest.TestCase):
 def test_each_weather_has_independent_expected_levels(self):
  expected={'sunny':(100,100),'clear-night':(100,100),'partlycloudy':(90,100),
   'cloudy':(75,100),'fog':(75,100),'rainy':(60,110),'snowy':(60,110),
   'snowy-rainy':(60,110),'windy':(75,115),'windy-variant':(75,115),
   'pouring':(50,120),'hail':(50,120),'lightning':(50,130),'lightning-rainy':(50,130)}
  for weather,values in expected.items():
   with self.subTest(weather=weather):
    s=Sim(weather,states={'number.light_scale':'20','number.tidal':'20'});s.run()
    self.assertEqual((int(s.states['number.light_scale']),int(s.states['number.tidal'])),values)
 def test_light_and_pump_settings_are_not_shared(self):
  s=Sim('rainy',inputs={'light_rainy_pct':42,'pump_rainy_pct':85});s.run()
  self.assertEqual([v for _,_,v in s.calls],[42,85])
 def test_unknown_and_nonstandard_weather_does_not_restore_sunny(self):
  for weather in ['unknown','unavailable','','exceptional','hurricane',None]:
   with self.subTest(weather=weather):self.assertEqual(Sim(weather).run(),[])
 def test_modes_and_restore_unknown_or_active_block_both(self):
  for e in ['switch.feed','input_boolean.maint','input_boolean.restore']:
   for value in ['on','unknown','unavailable']:
    with self.subTest(entity=e,value=value):self.assertEqual(Sim('rainy',states={e:value}).run(),[])
 def test_off_or_unavailable_light_does_not_block_pump_or_turn_light_on(self):
  for value in ['off','unknown','unavailable']:
   self.assertEqual(Sim('rainy',states={'light.coral':value}).run(),[('number.set_value','number.tidal',110)])
 def test_manual_and_viewing_light_not_overridden(self):
  for mode in ['manual','viewing',None]:
   self.assertEqual(Sim('rainy',attrs={('light.coral','active_mode'):mode}).run(),[('number.set_value','number.tidal',110)])
  self.assertEqual(Sim('rainy',attrs={('light.coral','active_mode'):'feeding'}).run(),[])
 def test_off_pump_and_manual_storm_are_not_overridden(self):
  for changes in [{'fan.wave':'off'},{'fan.wave':'unavailable'},{'select.run':'manual'},
    {'select.run':'unknown'},{'sensor.flow':'feed'},{'sensor.flow':'off'},
    {'sensor.flow':'unavailable'},{'sensor.flow':'mystery'}]:
   self.assertEqual(Sim('rainy',states=changes).run(),[('number.set_value','number.light_scale',60)])
 def test_missing_number_only_skips_its_branch(self):
  for value in ['unknown','unavailable','nan','inf']:
   self.assertEqual(Sim('rainy',states={'number.light_scale':value}).run(),[('number.set_value','number.tidal',110)])
   self.assertEqual(Sim('rainy',states={'number.tidal':value}).run(),[('number.set_value','number.light_scale',60)])
 def test_pending_curve_recovery_not_overwritten(self):
  self.assertEqual(Sim('rainy',attrs={('light.coral','schedule_recovery_required'):True}).run(),[('number.set_value','number.tidal',110)])
  self.assertEqual(Sim('rainy',attrs={('number.tidal','recovery_required'):True}).run(),[('number.set_value','number.light_scale',60)])
 def test_ceiling_and_quantization_never_exceed_cap(self):
  for cap,expected in [(200,120),(115,115),(73,73),(10,10),(67,67)]:
   s=Sim('pouring',inputs={'pump_ceiling':cap});s.run();self.assertEqual(int(s.states['number.tidal']),expected)
 def test_invalid_settings_are_skipped_and_numeric_bounds_held(self):
  for bad in ['nan','unknown',None]:
   self.assertEqual(Sim('rainy',inputs={'pump_rainy_pct':bad}).run(),[('number.set_value','number.light_scale',60)])
   self.assertEqual(Sim('rainy',inputs={'light_rainy_pct':bad}).run(),[('number.set_value','number.tidal',110)])
  for cap in [0,201,'unknown']:
   self.assertEqual(Sim('rainy',inputs={'pump_ceiling':cap}).run(),[('number.set_value','number.light_scale',60)])
  s=Sim('rainy',inputs={'light_rainy_pct':500,'pump_rainy_pct':200},states={'number.light_scale':'20','number.tidal':'20'});s.run()
  self.assertEqual((s.states['number.light_scale'],s.states['number.tidal']),('200','130'))
 def test_repeated_run_is_idempotent(self):
  s=Sim('rainy');s.run();s.calls=[];self.assertEqual(s.run(),[])
 def test_weather_clear_restores_configured_normal_not_hardcoded_full(self):
  s=Sim('rainy',inputs={'light_sunny_pct':92,'pump_sunny_pct':75});s.run();s.calls=[]
  s.states['weather.home']='sunny';s.run()
  self.assertEqual(s.calls,[('number.set_value','number.light_scale',92),('number.set_value','number.tidal',75)])
 def test_each_service_failure_does_not_block_other_target(self):
  for entity in ['number.light_scale','number.tidal']:
   s=Sim('rainy',fail=[entity]);self.assertEqual(len(s.run()),2)
 def test_mode_or_weather_change_between_services_cancels_remaining_write(self):
  for e,v in [('switch.feed','on'),('input_boolean.maint','on'),('input_boolean.restore','on'),('weather.home','sunny'),('select.run','manual')]:
   def change(s,entity):
    if entity=='number.light_scale':s.states[e]=v
   self.assertEqual(Sim('rainy',hook=change).run(),[('number.set_value','number.light_scale',60)])
 def test_storm_manual_to_tide_recovery_reapplies_without_mode_command(self):
  s=Sim('lightning',states={'select.run':'manual','number.tidal':'80'});s.run();s.calls=[]
  s.states['select.run']='tide';s.run();self.assertEqual(s.calls,[('number.set_value','number.tidal',130)])
 def test_mode_end_or_availability_recovery_reconciles_current_weather(self):
  for e in ['switch.feed','input_boolean.maint','input_boolean.restore']:
   s=Sim('rainy',states={e:'on'});self.assertEqual(s.run(),[]);s.states[e]='off';self.assertEqual(len(s.run()),2)
  s=Sim('rainy',states={'number.light_scale':'unavailable'});s.run();s.calls=[]
  s.states['number.light_scale']='100';self.assertEqual(s.run(),[('number.set_value','number.light_scale',60)])
 def test_only_allowed_targets_and_no_device_commands_in_blueprint(self):
  for row in BP['action']:
   for call in row.get('then',[]):
    self.assertEqual(call['service'],'number.set_value')
    self.assertIn(call['target']['entity_id'],['light_dimming','pump_tidal'])
  self.assertEqual(BP['mode'],'restart')
  self.assertFalse(any('time' in str(t.get('platform','')) for t in BP['trigger']))
  entity_triggers=BP['trigger'][0]['entity_id']
  for key in ['weather_entity','feeding_switch','maintenance_toggle','maintenance_restore_marker','pump_run_mode']:
   self.assertIn(key,entity_triggers)
  self.assertEqual({(str(t['entity_id']),t['from']) for t in BP['trigger'] if 'from' in t},
   {(key,state) for key in ['light_dimming','pump_tidal'] for state in ['unknown','unavailable']})
 def test_old_or_unknown_entity_max_rejects_unsupported_gain(self):
  for maximum in [100,None,'unknown']:
   s=Sim('rainy',attrs={('number.tidal','max'):maximum})
   self.assertEqual(s.run(),[('number.set_value','number.light_scale',60)])
  s=Sim('sunny',states={'number.tidal':'80'},attrs={('number.tidal','max'):100})
  self.assertEqual(s.run(),[('number.set_value','number.tidal',100)])
 def test_gain_ceiling_is_independent_of_entity_cap(self):
  s=Sim('lightning',inputs={'pump_ceiling':120});s.run();self.assertEqual(s.states['number.tidal'],'120')
  s=Sim('lightning',attrs={('number.tidal','max'):120});s.run();self.assertEqual(s.states['number.tidal'],'120')
 def test_inputs_complete_and_all_whole_tank_names_brand_neutral(self):
  def walk(v):
   if isinstance(v,Input):self.assertIn(v,BP['blueprint']['input'])
   elif isinstance(v,dict):
    for x in v.values():walk(x)
   elif isinstance(v,list):
    for x in v:walk(x)
  walk(BP)
  for p in (ROOT/'blueprints/automation/zetlight_led').glob('whole_tank*.yaml'):
   name=yaml.load(p.read_text(),Loader=Loader)['blueprint']['name']
   self.assertTrue(name.startswith('整缸联动 —'),(p,name));self.assertNotIn('积光',name)

if __name__=='__main__':unittest.main()

class HeadroomWeatherTests(unittest.TestCase):
 def test_app_gain_clamps_dynamic_max_at_integer_step(self):
  for maximum in [148,119,100]:
   s=Sim('lightning',inputs={'pump_lightning_pct':200,'pump_ceiling':200},attrs={('number.tidal','max'):maximum})
   s.run();self.assertLessEqual(float(s.states['number.tidal']),maximum)
 def test_unknown_gain_basis_and_external_edit_do_not_write(self):
  s=Sim('rainy',attrs={('number.tidal','gain_basis'):None,('number.light_scale','external_schedule_conflict'):True})
  self.assertEqual(s.run(),[])
