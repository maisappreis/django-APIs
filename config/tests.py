from django.test import SimpleTestCase, override_settings


@override_settings(DEBUG=False)
class DeploymentRoutingTest(SimpleTestCase):
    def test_root_redirects_to_swagger(self):
        response = self.client.get('/')

        self.assertRedirects(
            response,
            '/api/swagger/',
            fetch_redirect_response=False,
        )

    def test_admin_static_asset_is_served(self):
        response = self.client.get('/static/admin/css/base.css')

        self.assertEqual(response.status_code, 200)
