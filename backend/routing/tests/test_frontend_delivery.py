from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings


class FrontendDeliveryTests(SimpleTestCase):
    def test_invalid_asset_paths_return_404_instead_of_crashing(self):
        self.client.raise_request_exception = False
        with TemporaryDirectory() as directory, override_settings(FRONTEND_DIST=Path(directory), DEBUG=False):
            (Path(directory) / 'assets').mkdir()
            for url in ('/assets/%00.js', '/assets/' + 'a' * 300 + '.js'):
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 404)

    def test_production_root_and_bundled_assets(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            (root / 'index.html').write_text('<html>Assessment</html>')
            (root / 'assets' / 'index-123.js').write_text('console.log("ready")')
            with override_settings(FRONTEND_DIST=root, DEBUG=False):
                response = self.client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Assessment', b''.join(response.streaming_content))
                response = self.client.get('/assets/index-123.js')
                self.assertEqual(response.status_code, 200)
                self.assertIn('javascript', response['Content-Type'])
                response.close()
                for url in ('/assets/../index.html', '/assets/missing.js', '/api/missing/', '/.env'):
                    self.assertEqual(self.client.get(url).status_code, 404)
