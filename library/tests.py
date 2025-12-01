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

    def test_loan_additional_days(self):
        client = APIClient()
        response = client.post(f'/api/loans/{self.loan.id}/extend_due_date/', {'additional_days': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.json()
        new_due_date = timezone.now().date() + timedelta(days=24)
        self.assertEqual(result["due_date"], datetime.strftime(new_due_date, '%Y-%m-%d'))
    
    def test_loan_additional_days_invalid(self):
        client = APIClient()
        response = client.post(f'/api/loans/{self.loan.id}/extend_due_date/', {'additional_days': -1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.due_date, timezone.now().date() + timedelta(days=14))
    
    def test_loan_additional_days_expired(self):
        client = APIClient()
        self.loan.due_date = timezone.now().date() - timedelta(days=15)
        self.loan.save()
        response = client.post(f'/api/loans/{self.loan.id}/extend_due_date/', {'additional_days': 10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.due_date, timezone.now().date() - timedelta(days=15))


class BookTest(TestCase):
    def setUp(self):
        author = Author.objects.create(
            first_name="Author1",
            last_name="Last1"
        )
        for i in range(15):
            Book.objects.create(
                title = f"Book{i}",
                author = author,
                isbn = f"12234{i}",
                genre = "fiction",
                available_copies = 1
            )

    def test_book_list_pagination(self):
        client = APIClient()
        response = client.get('/api/books/', {'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['results']), 5)
        self.assertEqual(response.json()['count'], 15)


class MemberTest(TestCase):
    def setUp(self):
        for i in range(1, 16):
            user = User.objects.create(
                username=f'Test{i}',
                email=f'test{i}@test{i}'
            )
            Member.objects.create(
                user=user
            )
        
        author = Author.objects.create(
            first_name="Author1",
            last_name="Last1"
        )
        book = Book.objects.create(
            title = "Book1",
            author = author,
            isbn = "12234",
            genre = "fiction",
            available_copies = 10
        )
        for i in range(1, 6):
            Loan.objects.create(
                book=book,
                member=Member.objects.get(id=i),
                due_date=timezone.now().date() + timedelta(days=14)
            )
        Loan.objects.create(
            book=book,
            member=Member.objects.get(id=1),
            due_date=timezone.now().date() + timedelta(days=14)
        )

    def test_top_active_members(self):
        client = APIClient()
        response = client.get('/api/members/top-active/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 5)
        self.assertEqual(response.json()[0]['active_loans'], 2)
        self.assertEqual(response.json()[1]['active_loans'], 1)