from datetime import timedelta, datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status
from .models import Author, Member, Book, Loan
from .tasks import check_overdue_loans


class LoanTest(TestCase):

    def setUp(self):
        
        author = Author.objects.create(
            first_name="Author1",
            last_name="Last1"
        )
        book = Book.objects.create(
            title = "Book1",
            author = author,
            isbn = "12234",
            genre = "fiction",
            available_copies = 1
        )
        user = User.objects.create(
            username='Test1',
            email='test1@test1'
        )
        member = Member.objects.create(
            user=user
        )
        self.loan = Loan.objects.create(
            book=book,
            member=member,
            due_date=timezone.now().date() + timedelta(days=14)
        )

    @patch('library.tasks.send_mail')
    def test_check_overdue_loans(self, mock_send_mail):
        mock_send_mail.return_value = 1
        self.loan.due_date = timezone.now().date() - timedelta(days=15)
        self.loan.save()
        check_overdue_loans()
        mock_send_mail.assert_called_once()
        kwargs = mock_send_mail.call_args[1]
        self.assertEqual(kwargs["subject"], "Book Loaned with due date expired.")
        self.assertEqual(kwargs["recipient_list"], [self.loan.member.user.email])
