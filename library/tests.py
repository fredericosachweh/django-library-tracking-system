from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

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

    @patch('django.core.mail.send_mail')
    def test_check_overdue_loans(self, mock_send_mail):
        self.loan.due_date = timezone.now().date() - timedelta(days=15)
        self.loan.save()
        check_overdue_loans()
        book_title = self.loan.book.title
        args, kwargs = mock_send_mail.call_args
        subject = args[0]
        # Assert that send_mail was called with specific arguments
        self.assertEqual(subject, f'Hello {self.loan.member.user.username},\n\nYou have loaned "{book_title}".\nPlease return it now.')

