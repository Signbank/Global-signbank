from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from signbank.feedback.views import _get_admin_emails, _send_feedback_email


class GetAdminEmailsTests(TestCase):

    @override_settings(ADMINS=[('Alice', 'alice@example.com'), ('Bob', 'bob@example.com')])
    def test_returns_all_admin_emails(self):
        emails = _get_admin_emails()
        self.assertEqual(emails, ['alice@example.com', 'bob@example.com'])

    @override_settings(ADMINS=[])
    def test_returns_empty_list_when_no_admins(self):
        emails = _get_admin_emails()
        self.assertEqual(emails, [])


class SendFeedbackEmailTests(TestCase):

    @override_settings(ADMINS=[('Admin', 'admin@example.com')], DEBUG_EMAILS_ON=False,
                       DEFAULT_FROM_EMAIL='from@example.com')
    @patch('signbank.feedback.views.send_mail')
    @patch('signbank.feedback.views.generate_communication')
    def test_send_general_feedback_email(self, mock_generate, mock_send_mail):
        mock_generate.return_value = ('Test subject', 'Test message body')

        context = {'user': MagicMock(), 'comment': 'Test comment', 'site': MagicMock()}
        _send_feedback_email('feedback_general_email', context)

        mock_generate.assert_called_once_with('feedback_general_email', context)
        mock_send_mail.assert_called_once_with(
            'Test subject', 'Test message body', 'from@example.com', ['admin@example.com']
        )

    @override_settings(ADMINS=[], DEBUG_EMAILS_ON=False)
    @patch('signbank.feedback.views.send_mail')
    @patch('signbank.feedback.views.generate_communication')
    def test_no_email_sent_when_no_admins(self, mock_generate, mock_send_mail):
        context = {'user': MagicMock(), 'comment': 'Test comment', 'site': MagicMock()}
        _send_feedback_email('feedback_general_email', context)

        mock_generate.assert_not_called()
        mock_send_mail.assert_not_called()

    @override_settings(ADMINS=[('Admin', 'admin@example.com')], DEBUG_EMAILS_ON=True)
    @patch('signbank.feedback.views.send_mail')
    @patch('signbank.feedback.views.generate_communication')
    def test_no_email_sent_in_debug_mode(self, mock_generate, mock_send_mail):
        mock_generate.return_value = ('Test subject', 'Test message body')

        context = {'user': MagicMock(), 'comment': 'Test comment', 'site': MagicMock()}
        _send_feedback_email('feedback_general_email', context)

        mock_generate.assert_called_once()
        mock_send_mail.assert_not_called()

    @override_settings(ADMINS=[('Admin', 'admin@example.com')], DEBUG_EMAILS_ON=False,
                       DEFAULT_FROM_EMAIL='from@example.com')
    @patch('signbank.feedback.views.send_mail')
    @patch('signbank.feedback.views.generate_communication')
    def test_send_missingsign_feedback_email(self, mock_generate, mock_send_mail):
        mock_generate.return_value = ('Missing sign subject', 'Missing sign message')

        context = {
            'user': MagicMock(),
            'meaning': 'hello',
            'comments': 'some comment',
            'signlanguage': 'ASL',
            'site': MagicMock()
        }
        _send_feedback_email('feedback_missingsign_email', context)

        mock_generate.assert_called_once_with('feedback_missingsign_email', context)
        mock_send_mail.assert_called_once_with(
            'Missing sign subject', 'Missing sign message', 'from@example.com', ['admin@example.com']
        )

    @override_settings(ADMINS=[('Admin', 'admin@example.com')], DEBUG_EMAILS_ON=False,
                       DEFAULT_FROM_EMAIL='from@example.com')
    @patch('signbank.feedback.views.send_mail')
    @patch('signbank.feedback.views.generate_communication')
    def test_send_sign_feedback_email(self, mock_generate, mock_send_mail):
        mock_generate.return_value = ('Sign feedback subject', 'Sign feedback message')

        context = {
            'user': MagicMock(),
            'comment': 'nice sign',
            'gloss': 'HELLO',
            'site': MagicMock()
        }
        _send_feedback_email('feedback_sign_email', context)

        mock_generate.assert_called_once_with('feedback_sign_email', context)
        mock_send_mail.assert_called_once_with(
            'Sign feedback subject', 'Sign feedback message', 'from@example.com', ['admin@example.com']
        )

    @override_settings(ADMINS=[('Admin', 'admin@example.com')], DEBUG_EMAILS_ON=False,
                       DEFAULT_FROM_EMAIL='from@example.com')
    @patch('signbank.feedback.views.send_mail')
    @patch('signbank.feedback.views.generate_communication')
    def test_send_morpheme_feedback_email(self, mock_generate, mock_send_mail):
        mock_generate.return_value = ('Morpheme feedback subject', 'Morpheme feedback message')

        context = {
            'user': MagicMock(),
            'comment': 'nice morpheme',
            'morpheme': 'TEST-MORPHEME',
            'site': MagicMock()
        }
        _send_feedback_email('feedback_morpheme_email', context)

        mock_generate.assert_called_once_with('feedback_morpheme_email', context)
        mock_send_mail.assert_called_once_with(
            'Morpheme feedback subject', 'Morpheme feedback message', 'from@example.com', ['admin@example.com']
        )
