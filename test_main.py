import unittest
from unittest.mock import patch, MagicMock
import os
from datetime import datetime
from main import add_expense_to_airtable, get_budget_from_airtable, update_budget_in_airtable, add_budget_to_airtable

class TestTelegramBotFunctions(unittest.TestCase):

    def test_environment_variables(self):
        required_vars = ['AIRTABLE_BASE_ID', 'AIRTABLE_TOKEN','TELEGRAM_TOKEN', 'NOTION_API_TOKEN']
        for var in required_vars:
            with self.subTest(var=var):
                self.assertIn(var, os.environ, f'{var} is not set in the environment')
                self.assertIsNotNone(os.environ[var], f'{var} should not be None')
                self.assertNotEqual(os.environ[var], '', f'{var} should not be an empty string')

    @patch('requests.post')
    def test_add_expense_to_airtable(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "rec12345", "fields": {}}
        mock_post.return_value = mock_response

        status_code, response = add_expense_to_airtable("2024-05-29", "Jedzenie", "Konto1", 50.00, "Obiad")
        self.assertEqual(status_code, 200)
        self.assertIn("id", response)
        self.assertEqual(response["id"], "rec12345")

    @patch('requests.get')
    def test_get_budget_from_airtable(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": [{"id": "rec12345", "fields": {"Remaining": 500}}]}
        mock_get.return_value = mock_response

        budget = get_budget_from_airtable("Jedzenie", "2024-05")
        self.assertIsNotNone(budget)
        self.assertEqual(budget['id'], "rec12345")
        self.assertEqual(budget["fields"]["Remaining"], 500)

    @patch('requests.patch')
    def test_update_budget_in_airtable(self, mock_patch):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "rec12345", "fields": {"Remaining": 450}}
        mock_patch.return_value = mock_response

        status_code, response = update_budget_in_airtable("rec12345", 450)
        self.assertEqual(status_code, 200)
        self.assertIn("id", response)
        self.assertEqual(response["id"], "rec12345")
        self.assertEqual(response["fields"]["Remaining"], 450)

    @patch('requests.post')
    def test_add_budget_to_airtable(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "rec12345", "fields": {"Category": "Jedzenie", "Budget": 1000, "Remaining": 1000}}
        mock_post.return_value = mock_response

        status_code, response = add_budget_to_airtable("Jedzenie", 1000, "2024-06")
        self.assertEqual(status_code, 200)
        self.assertIn("id", response)
        self.assertEqual(response["id"], "rec12345")
        self.assertEqual(response["fields"]["Category"], "Jedzenie")
        self.assertEqual(response["fields"]["Budget"], 1000)
        self.assertEqual(response["fields"]["Remaining"], 1000)

if __name__ == '__main__':
    unittest.main()
