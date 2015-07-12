import time

from ichnaea.models import Radio
from ichnaea.api.submit.tests.base import BaseSubmitTest
from ichnaea.tests.base import CeleryAppTestCase
from ichnaea.tests.factories import (
    CellFactory,
    WifiFactory,
)


class TestSubmitV3(BaseSubmitTest, CeleryAppTestCase):

    url = '/v2/geosubmit'
    metric = 'geosubmit2'
    metric_url = 'request.v2.geosubmit'
    status = 200
    radio_id = 'radioType'
    cells_id = 'cellTowers'

    def _one_cell_query(self, radio=True):
        cell = CellFactory.build()
        query = {
            'position': {
                'latitude': cell.lat,
                'longitude': cell.lon,
            },
            'cellTowers': [{
                'mobileCountryCode': cell.mcc,
                'mobileNetworkCode': cell.mnc,
                'locationAreaCode': cell.lac,
                'cellId': cell.cid,
            }],
        }
        if radio:
            query['cellTowers'][0]['radioType'] = cell.radio.name
        return (cell, query)

    def test_cell(self):
        now_ms = int(time.time() * 1000)
        cell = CellFactory.build(radio=Radio.wcdma)
        response = self._post([{
            'carrier': 'Some Carrier',
            'homeMobileCountryCode': cell.mcc,
            'homeMobileNetworkCode': cell.mnc,
            'timestamp': now_ms,
            'xtra_field': 1,
            'position': {
                'latitude': cell.lat,
                'longitude': cell.lon,
                'accuracy': 12.4,
                'altitude': 100.1,
                'altitudeAccuracy': 23.7,
                'age': 1,
                'heading': 45.0,
                'pressure': 1013.25,
                'source': 'fused',
                'speed': 3.6,
                'xtra_field': 2,
            },
            'connection': {
                'ip': self.geoip_data['London']['ip'],
                'xtra_field': 3,
            },
            'cellTowers': [{
                'radioType': 'umts',
                'mobileCountryCode': cell.mcc,
                'mobileNetworkCode': cell.mnc,
                'locationAreaCode': cell.lac,
                'cellId': cell.cid,
                'primaryScramblingCode': cell.psc,
                'age': 3,
                'asu': 31,
                'serving': 1,
                'signalStrength': -51,
                'timingAdvance': 1,
                'xtra_field': 4,
            }]},
        ], api_key='test')
        # check that we get an empty response
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {})

        self._assert_queue_size(1)
        item = self.queue.dequeue(self.queue.queue_key())[0]
        self.assertEqual(item['metadata']['api_key'], 'test')
        report = item['report']
        self.assertEqual(report['timestamp'], now_ms)
        self.assertEqual(report['carrier'], 'Some Carrier')
        self.assertEqual(report['homeMobileCountryCode'], cell.mcc)
        self.assertEqual(report['homeMobileNetworkCode'], cell.mnc)
        self.assertFalse('xtra_field' in report)
        position = report['position']
        self.assertEqual(position['latitude'], cell.lat)
        self.assertEqual(position['longitude'], cell.lon)
        self.assertEqual(position['accuracy'], 12.4)
        self.assertEqual(position['age'], 1)
        self.assertEqual(position['altitude'], 100.1)
        self.assertEqual(position['altitudeAccuracy'], 23.7)
        self.assertEqual(position['heading'], 45.0)
        self.assertEqual(position['pressure'], 1013.25)
        self.assertEqual(position['source'], 'fused')
        self.assertEqual(position['speed'], 3.6)
        self.assertFalse('xtra_field' in position)
        self.assertFalse('connection' in report)
        cells = report['cellTowers']
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]['radioType'], 'wcdma')
        self.assertEqual(cells[0]['mobileCountryCode'], cell.mcc)
        self.assertEqual(cells[0]['mobileNetworkCode'], cell.mnc)
        self.assertEqual(cells[0]['locationAreaCode'], cell.lac)
        self.assertEqual(cells[0]['cellId'], cell.cid)
        self.assertEqual(cells[0]['primaryScramblingCode'], cell.psc)
        self.assertEqual(cells[0]['age'], 3)
        self.assertEqual(cells[0]['asu'], 31)
        self.assertEqual(cells[0]['serving'], 1)
        self.assertEqual(cells[0]['signalStrength'], -51)
        self.assertEqual(cells[0]['timingAdvance'], 1)
        self.assertFalse('xtra_field' in cells[0])

    def test_wifi(self):
        wifi = WifiFactory.build()
        self._post([{
            'position': {
                'latitude': wifi.lat,
                'longitude': wifi.lon,
            },
            'wifiAccessPoints': [{
                'macAddress': wifi.key,
                'ssid': 'my-wifi',
                'age': 3,
                'channel': 5,
                'frequency': 2437,
                'radioType': '802.11n',
                'signalStrength': -90,
                'signalToNoiseRatio': 5,
                'xtra_field': 3,
            }]},
        ])

        self._assert_queue_size(1)
        item = self.queue.dequeue(self.queue.queue_key())[0]
        self.assertEqual(item['metadata']['api_key'], None)
        report = item['report']
        self.assertTrue('timestamp' in report)
        position = report['position']
        self.assertEqual(position['latitude'], wifi.lat)
        self.assertEqual(position['longitude'], wifi.lon)
        wifis = item['report']['wifiAccessPoints']
        self.assertEqual(len(wifis), 1)
        self.assertEqual(wifis[0]['macAddress'], wifi.key)
        self.assertEqual(wifis[0]['age'], 3),
        self.assertEqual(wifis[0]['channel'], 5),
        self.assertEqual(wifis[0]['frequency'], 2437),
        self.assertEqual(wifis[0]['radioType'], '802.11n')
        self.assertEqual(wifis[0]['signalStrength'], -90),
        self.assertEqual(wifis[0]['signalToNoiseRatio'], 5),
        self.assertFalse('ssid' in wifis[0])
        self.assertFalse('xtra_field' in wifis[0])

    def test_bluetooth(self):
        wifi = WifiFactory.build()
        self._post([{
            'position': {
                'latitude': wifi.lat,
                'longitude': wifi.lon,
            },
            'bluetoothBeacons': [{
                'macAddress': wifi.key,
                'name': 'my-beacon',
                'age': 3,
                'signalStrength': -90,
                'xtra_field': 4,
            }],
            'wifiAccessPoints': [{
                'signalStrength': -52,
            }]},
        ])

        self._assert_queue_size(1)
        item = self.queue.dequeue(self.queue.queue_key())[0]
        report = item['report']
        self.assertTrue('timestamp' in report)
        position = report['position']
        self.assertEqual(position['latitude'], wifi.lat)
        self.assertEqual(position['longitude'], wifi.lon)
        blues = report['bluetoothBeacons']
        self.assertEqual(len(blues), 1)
        self.assertEqual(blues[0]['macAddress'], wifi.key)
        self.assertEqual(blues[0]['age'], 3),
        self.assertEqual(blues[0]['name'], 'my-beacon'),
        self.assertEqual(blues[0]['signalStrength'], -90),
        self.assertFalse('xtra_field' in blues[0])
        wifis = report['wifiAccessPoints']
        self.assertEqual(len(wifis), 1)

    def test_batches(self):
        batch = 110
        wifis = WifiFactory.build_batch(batch)
        items = [{
            'position': {
                'latitude': wifi.lat,
                'longitude': wifi.lon},
            'wifiAccessPoints': [
                {'macAddress': wifi.key},
            ]} for wifi in wifis]

        # add a bad one, this will just be skipped
        items.append({'latitude': 10.0, 'longitude': 10.0, 'whatever': 'xx'})
        self._post(items)
        self._assert_queue_size(batch)

    def test_error(self):
        wifi = WifiFactory.build()
        self._post([{
            'position': {
                'latitude': wifi.lat,
                'longitude': wifi.lon,
            },
            'wifiAccessPoints': [{
                'macAddress': 10,
            }],
        }], status=400)
        self._assert_queue_size(0)
