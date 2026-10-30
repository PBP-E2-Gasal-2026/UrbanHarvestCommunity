from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from authentication.models import Role, Session, User

from .forms import PostForm
from .models import Comment, Post
from .templatetags.forum_tags import waktu_lalu, waktu_lalu_singkat


class ForumTestCase(TestCase):
    def setUp(self):
        farmer = Role.objects.create(name='farmer', description='Petani')
        self.rani = User.objects.create_user(username='rani', email='rani@example.com', password='x')
        self.budi = User.objects.create_user(username='budi', email='budi@example.com', password='x')
        self.rani.roles.add(farmer)
        self.budi.roles.add(farmer)
        self.post = Post.objects.create(creator=self.rani, content='Tomat saya kena hama, ada saran?')
        self.comment = Comment.objects.create(post=self.post, creator=self.rani, content='Sudah coba pestisida nabati.')

    def login(self, user):
        # Middleware single-session modul autentikasi membutuhkan baris Session.
        self.client.force_login(user)
        Session.objects.update_or_create(
            session_token=self.client.session.session_key,
            defaults={'user': user, 'expires_at': timezone.now() + timedelta(days=1)},
        )


class ForumPageTests(ForumTestCase):
    def test_guest_can_read_forum_and_feed(self):
        self.assertContains(self.client.get(reverse('community_forum:show_community')), 'Tomat saya kena hama')
        self.assertContains(self.client.get(reverse('community_forum:feed')), 'Tomat saya kena hama')

    def test_forum_renders_for_comment_owner(self):
        # Regresi: link edit/hapus komentar dulu memicu NoReverseMatch (error 500).
        self.login(self.rani)
        response = self.client.get(reverse('community_forum:show_community'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('community_forum:edit_comment', args=[self.post.pk, self.comment.pk]))
        self.assertContains(response, reverse('community_forum:delete_comment', args=[self.post.pk, self.comment.pk]))

    def test_edit_controls_only_for_owner(self):
        self.login(self.budi)
        response = self.client.get(reverse('community_forum:show_community'))
        self.assertNotContains(response, reverse('community_forum:edit_post', args=[self.post.pk]))
        self.assertNotContains(response, reverse('community_forum:edit_comment', args=[self.post.pk, self.comment.pk]))

    def test_feed_popular_tab_orders_by_likes(self):
        newer = Post.objects.create(creator=self.budi, content='Post baru tanpa suka')
        self.post.likes.add(self.budi)
        latest = list(self.client.get(reverse('community_forum:feed')).context['post_list'])
        popular = list(self.client.get(reverse('community_forum:feed'), {'urut': 'populer'}).context['post_list'])
        self.assertEqual(latest[0], newer)
        self.assertEqual(popular[0], self.post)
        self.assertEqual(self.client.get(reverse('community_forum:feed'), {'urut': 'asal'}).context['urut'], 'terbaru')

    def test_post_from_feed_returns_to_feed_and_rejects_external_next(self):
        self.login(self.budi)
        feed_url = reverse('community_forum:feed')
        response = self.client.post(reverse('community_forum:create_post'), {'content': 'Dari feed', 'next': feed_url})
        self.assertEqual(response['Location'], feed_url)
        response = self.client.post(reverse('community_forum:create_post'),
                                    {'content': 'Coba alihkan', 'next': 'https://evil.example.com/'})
        self.assertTrue(response['Location'].startswith(reverse('community_forum:show_community')))

    def test_feed_lists_posts_with_counts(self):
        self.post.likes.add(self.budi)
        response = self.client.get(reverse('community_forum:feed'))
        posts = list(response.context['post_list'])
        self.assertEqual(posts, [self.post])
        self.assertEqual((posts[0].like_count, posts[0].comment_count), (1, 1))


class PostTests(ForumTestCase):
    def test_guest_cannot_create_post(self):
        response = self.client.post(reverse('community_forum:create_post'), {'content': 'Halo'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 1)

    def test_member_can_create_post(self):
        self.login(self.budi)
        self.client.post(reverse('community_forum:create_post'), {'content': 'Panen kangkung hari ini'})
        self.assertTrue(Post.objects.filter(creator=self.budi, content='Panen kangkung hari ini').exists())

    def test_post_limited_to_1000_words(self):
        self.assertFalse(PostForm(data={'content': 'kata ' * 1001}).is_valid())
        self.assertTrue(PostForm(data={'content': 'kata ' * 1000}).is_valid())

    def test_owner_can_edit_and_delete(self):
        self.login(self.rani)
        self.client.post(reverse('community_forum:edit_post', args=[self.post.pk]), {'content': 'Sudah teratasi'})
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, 'Sudah teratasi')
        self.client.post(reverse('community_forum:delete_post', args=[self.post.pk]))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_other_user_cannot_edit_or_delete(self):
        self.login(self.budi)
        edit = self.client.post(reverse('community_forum:edit_post', args=[self.post.pk]), {'content': 'Diretas'})
        delete = self.client.post(reverse('community_forum:delete_post', args=[self.post.pk]))
        self.assertEqual((edit.status_code, delete.status_code), (404, 404))
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, 'Tomat saya kena hama, ada saran?')

    def test_delete_requires_post_method(self):
        self.login(self.rani)
        response = self.client.get(reverse('community_forum:delete_post', args=[self.post.pk]))
        self.assertEqual(response.status_code, 405)

    def test_like_via_ajax_returns_state(self):
        self.login(self.budi)
        url = reverse('community_forum:toggle_like', args=[self.post.pk])
        data = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
        self.assertEqual(data, {'liked': True, 'count': 1})
        data = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
        self.assertEqual(data, {'liked': False, 'count': 0})

    def test_like_without_js_returns_to_post(self):
        self.login(self.budi)
        response = self.client.post(reverse('community_forum:toggle_like', args=[self.post.pk]))
        self.assertEqual(response['Location'], f"{reverse('community_forum:show_community')}#post-{self.post.pk}")

    def test_like_toggles(self):
        self.login(self.budi)
        url = reverse('community_forum:toggle_like', args=[self.post.pk])
        self.client.post(url)
        self.assertTrue(self.post.likes.filter(pk=self.budi.pk).exists())
        self.client.post(url)
        self.assertFalse(self.post.likes.filter(pk=self.budi.pk).exists())


class CommentTests(ForumTestCase):
    def test_member_can_comment(self):
        self.login(self.budi)
        response = self.client.post(reverse('community_forum:create_comment', args=[self.post.pk]),
                                    {'content': 'Coba semprot air sabun.'})
        self.assertRedirects(response, f"{reverse('community_forum:show_community')}#post-{self.post.pk}",
                             fetch_redirect_response=False)
        self.assertEqual(self.post.comments.count(), 2)

    def test_invalid_comment_shows_form(self):
        self.login(self.budi)
        response = self.client.post(reverse('community_forum:create_comment', args=[self.post.pk]), {'content': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tulis komentar')

    def test_edit_comment_page_has_edit_title(self):
        self.login(self.rani)
        response = self.client.get(reverse('community_forum:edit_comment', args=[self.post.pk, self.comment.pk]))
        self.assertContains(response, 'Edit komentar')

    def test_owner_can_edit_and_delete_comment(self):
        self.login(self.rani)
        self.client.post(reverse('community_forum:edit_comment', args=[self.post.pk, self.comment.pk]),
                         {'content': 'Sudah berhasil'})
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, 'Sudah berhasil')
        self.client.post(reverse('community_forum:delete_comment', args=[self.post.pk, self.comment.pk]))
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_other_user_cannot_touch_comment(self):
        self.login(self.budi)
        url = reverse('community_forum:delete_comment', args=[self.post.pk, self.comment.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_comment_must_belong_to_post_in_url(self):
        other_post = Post.objects.create(creator=self.budi, content='Post lain')
        self.login(self.rani)
        url = reverse('community_forum:edit_comment', args=[other_post.pk, self.comment.pk])
        self.assertEqual(self.client.get(url).status_code, 404)


class WaktuLaluTests(TestCase):
    def test_relative_time_in_indonesian(self):
        now = timezone.now()
        self.assertEqual(waktu_lalu(now), 'baru saja')
        self.assertEqual(waktu_lalu(now - timedelta(minutes=5)), '5 menit yang lalu')
        self.assertEqual(waktu_lalu(now - timedelta(hours=3)), '3 jam yang lalu')
        self.assertEqual(waktu_lalu(now - timedelta(days=2)), '2 hari yang lalu')
        self.assertEqual(waktu_lalu(None), '')

    def test_short_relative_time(self):
        now = timezone.now()
        self.assertEqual(waktu_lalu_singkat(now), 'baru')
        self.assertEqual(waktu_lalu_singkat(now - timedelta(minutes=5)), '5m')
        self.assertEqual(waktu_lalu_singkat(now - timedelta(hours=3)), '3j')
        self.assertEqual(waktu_lalu_singkat(now - timedelta(days=2)), '2h')
        old = timezone.localtime(now - timedelta(days=400))
        self.assertTrue(waktu_lalu_singkat(old).endswith(str(old.year)))

