"""Actual switch/client/coordinator semantics with no HA instance or device I/O."""
import ast
import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from test_recovery import Client, Coord, protocol

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/zetlight_led'

class Entity:
    def __class_getitem__(cls, item):
        return cls
    def __init__(self, coordinator):
        self.coordinator = coordinator

class Switch:
    pass

def load_switches():
    tree = ast.parse((ROOT / 'switch.py').read_text())
    nodes = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]
    nodes += [n for n in tree.body if isinstance(n, ast.ClassDef) or
              isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_setup_entry']
    namespace = dict(CoordinatorEntity=Entity, SwitchEntity=Switch, ZetlightCoordinator=Coord,
                     DeviceInfo=lambda **kw: kw, DOMAIN='zetlight_led',
                     EntityCategory=SimpleNamespace(CONFIG='config'))
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 str(ROOT / 'switch.py'), 'exec'), namespace)
    return namespace

SWITCHES = load_switches()

def client_with_options(cloud=1, phase=0, coral=0, moon=0):
    client = Client(None, 'fixture', 8855, protocol.DEFAULT_DEVICE_CODE)
    state = [cloud, phase, coral, moon]
    writes = []
    async def read():
        await asyncio.sleep(0)
        return protocol.OptionState(*state)
    async def request(frame, **kwargs):
        await asyncio.sleep(0)
        assert frame[0] == protocol.REQUEST_HEADER
        _, command, payload = protocol.parse_frame(bytes([protocol.RESPONSE_HEADER]) + frame[1:])
        writes.append((command, list(payload)))
        if command == protocol.CMD_SET_OPTIONS:
            state[:3] = payload
        elif command == protocol.CMD_SET_MOON:
            state[3] = payload[0]
        else:
            raise AssertionError('Unexpected device command')
    client.async_read_options = read
    client._request = request
    return client, state, writes

class EntityContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_identity_and_command_are_not_repurposed(self):
        c = SimpleNamespace(options=protocol.OptionState(1, 0, 0, 0),
                            async_set_moon=AsyncMock(), async_set_lunar_phase=AsyncMock())
        old = SWITCHES['ZetlightMoonSwitch'](c, 'fixture')
        self.assertEqual(old._attr_unique_id, 'fixture_moon_phase')
        self.assertEqual(old._attr_translation_key, 'moon_phase')
        self.assertEqual(old._attr_device_info['identifiers'], {('zetlight_led', 'fixture')})
        await old.async_turn_on(); await old.async_turn_off()
        self.assertEqual([a.args for a in c.async_set_moon.await_args_list], [(True,), (False,)])
        c.async_set_lunar_phase.assert_not_awaited()
    async def test_distinct_lunar_identity_and_callback(self):
        c = SimpleNamespace(options=None, async_set_moon=AsyncMock(), async_set_lunar_phase=AsyncMock())
        new = SWITCHES['ZetlightLunarPhaseSwitch'](c, 'fixture')
        self.assertEqual(new._attr_unique_id, 'fixture_lunar_phase')
        self.assertEqual(new._attr_translation_key, 'lunar_phase')
        await new.async_turn_on(); await new.async_turn_off()
        self.assertEqual([a.args for a in c.async_set_lunar_phase.await_args_list], [(True,), (False,)])
        c.async_set_moon.assert_not_awaited()
    async def test_independent_readback_and_missing_state(self):
        c = SimpleNamespace(options=None)
        moon = SWITCHES['ZetlightMoonSwitch'](c, 'fixture')
        lunar = SWITCHES['ZetlightLunarPhaseSwitch'](c, 'fixture')
        self.assertIsNone(moon.is_on); self.assertIsNone(lunar.is_on)
        for phase, light in [(0, 1), (1, 0), (0, 0), (1, 1)]:
            c.options = protocol.OptionState(0, phase, 0, light)
            self.assertEqual(moon.is_on, bool(light)); self.assertEqual(lunar.is_on, bool(phase))
        c.options = protocol.OptionState(0, 2, 0, 0)
        self.assertIsNone(lunar.is_on)
    async def test_setup_only_adds_entities_and_sends_no_command(self):
        c = SimpleNamespace(options=None, async_set_moon=AsyncMock(), async_set_lunar_phase=AsyncMock())
        added = []
        await SWITCHES['async_setup_entry'](None, SimpleNamespace(runtime_data=c, entry_id='fixture'), added.extend)
        self.assertEqual(len(added), 7)
        ids = [e._attr_unique_id for e in added]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn('fixture_moon_phase', ids); self.assertIn('fixture_lunar_phase', ids)
        c.async_set_moon.assert_not_awaited(); c.async_set_lunar_phase.assert_not_awaited()
    def test_translations_distinguish_semantics_without_changing_legacy_key(self):
        for path in [ROOT / 'strings.json', ROOT / 'translations/en.json', ROOT / 'translations/zh-Hans.json']:
            data = json.loads(path.read_text())['entity']['switch']
            self.assertIn('moon_phase', data); self.assertIn('lunar_phase', data)
            self.assertNotEqual(data['moon_phase']['name'], data['lunar_phase']['name'])
            if path.name == 'zh-Hans.json':
                self.assertEqual(data['moon_phase']['name'], '月光开关')
                self.assertEqual(data['lunar_phase']['name'], '月相模式')
            else:
                self.assertEqual(data['moon_phase']['name'], 'Moonlight')
                self.assertEqual(data['lunar_phase']['name'], 'Lunar phase')

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_lunar_write_preserves_cloud_coral_and_moon(self):
        for target in [True, False]:
            client, state, writes = client_with_options(phase=int(not target), coral=0 if target else 7, moon=1)
            await client.async_set_lunar_phase(target)
            self.assertEqual(state, [1, int(target), 0 if target else 7, 1])
            self.assertEqual(writes, [(protocol.CMD_SET_OPTIONS, [1, int(target), 0 if target else 7])])
    async def test_legacy_moon_write_never_touches_lunar_or_native_options(self):
        client, state, writes = client_with_options(phase=1, moon=0)
        await client.async_set_moon(True)
        self.assertEqual(state, [1, 1, 0, 1]); self.assertEqual(writes, [(protocol.CMD_SET_MOON, [1])])
    async def test_read_failure_never_guesses_flags_or_writes(self):
        client, _, _ = client_with_options()
        client.async_read_options = AsyncMock(side_effect=OSError('read unavailable'))
        client._request = AsyncMock()
        with self.assertRaises(OSError): await client.async_set_lunar_phase(True)
        client._request.assert_not_awaited()
    async def test_lunar_enable_does_not_silently_cancel_native_acclimation(self):
        for day in [1, 7, 10]:
            client, state, writes = client_with_options(coral=day)
            with self.assertRaisesRegex(OSError, 'acclimation'): await client.async_set_lunar_phase(True)
            self.assertEqual(state, [1, 0, day, 0]); self.assertEqual(writes, [])
    async def test_acclimation_enable_requires_lunar_off(self):
        client, state, writes = client_with_options(phase=1)
        with self.assertRaisesRegex(OSError, 'lunar'): await client.async_set_coral(True)
        self.assertEqual(state, [1, 1, 0, 0]); self.assertEqual(writes, [])
    async def test_concurrent_options_edits_do_not_lose_sibling_fields(self):
        for first, second in [('async_set_lunar_phase', 'async_set_auto_cloud'),
                              ('async_set_auto_cloud', 'async_set_lunar_phase')]:
            client, state, _ = client_with_options(cloud=0)
            await asyncio.gather(getattr(client, first)(True), getattr(client, second)(True))
            self.assertEqual(state, [1, 1, 0, 0])
    async def test_concurrent_conflicting_enable_never_sets_both_modes(self):
        for first, second in [('async_set_lunar_phase', 'async_set_coral'),
                              ('async_set_coral', 'async_set_lunar_phase')]:
            client, state, writes = client_with_options()
            results = await asyncio.gather(getattr(client, first)(True), getattr(client, second)(True), return_exceptions=True)
            self.assertEqual(sum(isinstance(r, OSError) for r in results), 1)
            self.assertEqual(len(writes), 1); self.assertFalse(state[1] and state[2])
    async def test_switch_to_real_coordinator_to_transport_and_refresh(self):
        client, state, writes = client_with_options(cloud=1, moon=1)
        c = Coord(None, client, 'fixture')
        c.options = await client.async_read_options()
        moon = SWITCHES['ZetlightMoonSwitch'](c, 'fixture')
        lunar = SWITCHES['ZetlightLunarPhaseSwitch'](c, 'fixture')
        await lunar.async_turn_on()
        self.assertTrue(lunar.is_on); self.assertTrue(moon.is_on)
        await moon.async_turn_off()
        self.assertTrue(lunar.is_on); self.assertFalse(moon.is_on)
        self.assertEqual(writes, [(protocol.CMD_SET_OPTIONS, [1, 1, 0]), (protocol.CMD_SET_MOON, [0])])
        self.assertEqual(state, [1, 1, 0, 0])
    async def test_target_readback_mismatch_is_reported(self):
        client, _, _ = client_with_options()
        client._request = AsyncMock()  # sent, but hardware did not apply it
        with self.assertRaisesRegex(OSError, 'unconfirmed'):
            await client.async_set_lunar_phase(True)
    async def test_sibling_field_change_is_not_reported_as_preserved(self):
        client, state, _ = client_with_options()
        async def changed_by_device(*args, **kwargs):
            state[:3] = [0, 1, 0]
        client._request = changed_by_device
        with self.assertRaisesRegex(OSError, 'unconfirmed'):
            await client.async_set_lunar_phase(True)
    async def test_postwrite_read_failure_marks_options_unknown_and_raises(self):
        client, _, _ = client_with_options()
        c = Coord(None, client, 'fixture'); c.options = protocol.OptionState(1, 0, 0, 0)
        client.async_read_options = AsyncMock(side_effect=[c.options, OSError('readback lost')])
        client._request = AsyncMock()
        lunar = SWITCHES['ZetlightLunarPhaseSwitch'](c, 'fixture')
        with self.assertRaises(OSError): await lunar.async_turn_on()
        self.assertIsNone(lunar.is_on)
    async def test_cancelled_write_marks_options_unknown_and_keeps_cancellation(self):
        client, _, _ = client_with_options()
        c = Coord(None, client, 'fixture'); c.options = protocol.OptionState(1, 0, 0, 0)
        lunar = SWITCHES['ZetlightLunarPhaseSwitch'](c, 'fixture')
        client._request = AsyncMock(side_effect=asyncio.CancelledError())
        with self.assertRaises(asyncio.CancelledError): await lunar.async_turn_on()
        self.assertIsNone(lunar.is_on)
    async def test_failed_write_does_not_invent_new_entity_state(self):
        client, _, _ = client_with_options()
        c = Coord(None, client, 'fixture'); c.options = await client.async_read_options()
        lunar = SWITCHES['ZetlightLunarPhaseSwitch'](c, 'fixture')
        client._request = AsyncMock(side_effect=OSError('send failed'))
        with self.assertRaises(OSError): await lunar.async_turn_on()
        self.assertIsNone(lunar.is_on)

if __name__ == '__main__': unittest.main()
