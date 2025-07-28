import json
from django.test import TestCase
from rest_framework.test import APIClient

class SwaggerSchemaTest(TestCase):
    """Smoke tests for the Swagger/OpenAPI endpoints"""
    def setUp(self):
        self.client = APIClient()

    def test_swagger_json(self):
        response = self.client.get('/swagger.json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('openapi', data)

    def test_swagger_ui(self):
        response = self.client.get('/swagger/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Swagger UI', content) 