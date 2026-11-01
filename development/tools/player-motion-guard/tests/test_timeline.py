from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'tools/read_timeline.py'
spec = importlib.util.spec_from_file_location('timeline', SOURCE)
timeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timeline)


class TimelineTests(unittest.TestCase):
    def test_identity_time_type_limit_and_incomplete_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            events = root/'events'
            events.mkdir()
            rows = [
                {'timeMillis':1,'type':'player_identity','data':{'playerName':'Probe','playerId':'probe-id'}},
                {'timeMillis':2,'type':'move','data':{'state':{'playerId':'probe-id','x':1}}},
                {'timeMillis':3,'type':'move','data':{'state':{'playerId':'other-id','x':2}}},
                {'timeMillis':4,'type':'hurt','data':{'playerId':'probe-id'}},
                {'timeMillis':5,'type':'move','data':{'state':{'playerId':'probe-id','x':3}}},
            ]
            (events/'events-probe-1.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows)+'{"partial":')
            result, report = timeline.read_events(root, player='Probe', since_millis=2, types=['move'], limit=1)
            self.assertEqual(result[0]['timeMillis'],5)
            self.assertEqual(report['matchedRecords'],2)
            self.assertEqual(report['incompleteTailLinesIgnored'],1)
            self.assertEqual(report['resolvedPlayer'],'probe-id')
            empty, _ = timeline.read_events(root, player='missing')
            self.assertEqual(empty,[])

    def test_reports_bounded_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'events').mkdir()
            (root/'events/events-probe-1.jsonl').write_text('{"timeMillis":1}\n')
            result, report = timeline.read_events(root, byte_limit=1)
            self.assertEqual(result,[])
            self.assertTrue(report['boundedScan'])


if __name__ == '__main__':
    unittest.main()
