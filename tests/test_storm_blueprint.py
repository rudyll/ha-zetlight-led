"""Regression: mode=restart must admit the clear-weather restoration run."""
from pathlib import Path
from types import SimpleNamespace
import unittest
import yaml
from jinja2 import Environment, StrictUndefined

class Loader(yaml.SafeLoader): pass
Loader.add_constructor('!input', lambda loader,node: loader.construct_scalar(node))

class StormTests(unittest.TestCase):
    def test_weather_transitions(self):
        path=Path(__file__).resolve().parents[1]/'blueprints/automation/zetlight_led/whole_tank_storm.yaml'
        bp=yaml.load(path.read_text(),Loader=Loader)
        self.assertEqual(bp['mode'],'restart')
        template=Environment(undefined=StrictUndefined).from_string(bp['condition'][0])
        def state(value): return None if value is None else SimpleNamespace(state=value)
        for old,new,expected in [('sunny','lightning',True),('lightning','sunny',True),('lightning','unavailable',True),('sunny','cloudy',False),(None,'sunny',False),(None,'lightning',True),('lightning',None,True)]:
            with self.subTest(old=old,new=new):
                actual=template.render(trigger=SimpleNamespace(from_state=state(old),to_state=state(new)),storm=['lightning','lightning-rainy']).strip()=='True'
                self.assertEqual(actual,expected)

if __name__=='__main__': unittest.main()
