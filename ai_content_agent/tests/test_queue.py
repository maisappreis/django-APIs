from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from ai_content_agent.queue import (
    enqueue_brand_visual_identity,
    enqueue_post_generation,
    enqueue_post_image_generation,
)
from ai_content_agent.tests.factories import create_batch, create_user


class QStashPublisherTest(TestCase):
    @override_settings(
        CONTENT_AGENT_QUEUE_BACKEND="qstash",
        QSTASH_TOKEN="qstash-secret",
        QSTASH_URL="https://qstash-us-east-1.upstash.io/",
        CONTENT_AGENT_JOB_TOKEN="job-secret",
        CONTENT_AGENT_PUBLIC_URL="https://api.example.com/",
        CONTENT_AGENT_WORKER_URL="",
    )
    @patch("ai_content_agent.queue.httpx.post")
    def test_enqueue_post_generation_publishes_authenticated_job(self, post):
        response = Mock()
        response.json.return_value = {"messageId": "msg-1"}
        post.return_value = response

        result = enqueue_post_generation(
            7,
            3,
            11,
            {"objective": "Leads", "quantity": 1},
        )

        self.assertEqual(result, {"messageId": "msg-1"})
        publish_url = post.call_args.args[0]
        self.assertEqual(
            publish_url,
            (
                "https://qstash-us-east-1.upstash.io/v2/publish/"
                "https://api.example.com/api/content-agent/jobs/"
                "post-generation/"
            ),
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "user_id": 7,
                "brand_id": 3,
                "batch_id": 11,
                "data": {"objective": "Leads", "quantity": 1},
            },
        )
        self.assertEqual(
            post.call_args.kwargs["headers"][
                "Upstash-Forward-X-Content-Agent-Job-Token"
            ],
            "job-secret",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Upstash-Retries"],
            "0",
        )
        response.raise_for_status.assert_called_once_with()

    @override_settings(
        CONTENT_AGENT_QUEUE_BACKEND="qstash",
        QSTASH_TOKEN="qstash-secret",
        QSTASH_URL="https://qstash-us-east-1.upstash.io/",
        CONTENT_AGENT_JOB_TOKEN="job-secret",
        CONTENT_AGENT_PUBLIC_URL="https://api.example.com/",
        CONTENT_AGENT_WORKER_URL="",
    )
    @patch("ai_content_agent.queue.httpx.post")
    def test_enqueue_publishes_authenticated_job(self, post):
        response = Mock()
        response.json.return_value = {"messageId": "msg-1"}
        post.return_value = response

        result = enqueue_post_image_generation(7, 11)

        self.assertEqual(result, {"messageId": "msg-1"})
        publish_url = post.call_args.args[0]
        self.assertEqual(
            publish_url,
            (
                "https://qstash-us-east-1.upstash.io/v2/publish/"
                "https://api.example.com/api/content-agent/jobs/"
                "post-images/"
            ),
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"user_id": 7, "batch_id": 11},
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer qstash-secret",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"][
                "Upstash-Forward-X-Content-Agent-Job-Token"
            ],
            "job-secret",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Upstash-Retries"],
            "0",
        )
        response.raise_for_status.assert_called_once_with()

    @override_settings(
        CONTENT_AGENT_QUEUE_BACKEND="qstash",
        QSTASH_TOKEN="qstash-secret",
        QSTASH_URL="https://qstash-us-east-1.upstash.io/",
        CONTENT_AGENT_JOB_TOKEN="job-secret",
        CONTENT_AGENT_PUBLIC_URL="https://api.example.com/",
        CONTENT_AGENT_WORKER_URL="https://content-agent-worker.run.app/",
    )
    @patch("ai_content_agent.queue.httpx.post")
    def test_enqueue_prefers_worker_url_for_generation_jobs(self, post):
        response = Mock()
        response.json.return_value = {"messageId": "msg-1"}
        post.return_value = response

        enqueue_post_generation(7, 3, 11, {"quantity": 1})

        self.assertEqual(
            post.call_args.args[0],
            (
                "https://qstash-us-east-1.upstash.io/v2/publish/"
                "https://content-agent-worker.run.app/api/content-agent/"
                "jobs/post-generation/"
            ),
        )
        response.raise_for_status.assert_called_once_with()

    @override_settings(
        CONTENT_AGENT_QUEUE_BACKEND="qstash",
        QSTASH_TOKEN="qstash-secret",
        QSTASH_URL="https://qstash-us-east-1.upstash.io/",
        CONTENT_AGENT_JOB_TOKEN="job-secret",
        CONTENT_AGENT_PUBLIC_URL="https://api.example.com/",
        CONTENT_AGENT_WORKER_URL="https://content-agent-worker.run.app/",
    )
    @patch("ai_content_agent.queue.httpx.post")
    def test_enqueue_brand_visual_identity_publishes_worker_job(self, post):
        response = Mock()
        response.json.return_value = {"messageId": "msg-1"}
        post.return_value = response

        result = enqueue_brand_visual_identity(7, 3)

        self.assertEqual(result, {"messageId": "msg-1"})
        self.assertEqual(
            post.call_args.args[0],
            (
                "https://qstash-us-east-1.upstash.io/v2/publish/"
                "https://content-agent-worker.run.app/api/content-agent/"
                "jobs/brand-visual-identity/"
            ),
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"user_id": 7, "brand_id": 3},
        )
        response.raise_for_status.assert_called_once_with()

    @override_settings(
        CONTENT_AGENT_QUEUE_BACKEND="qstash",
        QSTASH_TOKEN="",
        CONTENT_AGENT_JOB_TOKEN="",
        CONTENT_AGENT_PUBLIC_URL="",
        CONTENT_AGENT_WORKER_URL="",
    )
    def test_enqueue_requires_queue_configuration(self):
        with self.assertRaises(ImproperlyConfigured):
            enqueue_post_image_generation(7, 11)

    @override_settings(CONTENT_AGENT_QUEUE_BACKEND="inline")
    @patch("ai_content_agent.jobs.run_post_generation_job")
    def test_inline_backend_runs_generation_job_without_qstash_configuration(
        self,
        run_job,
    ):
        result = enqueue_post_generation(7, 3, 11, {"quantity": 1})

        self.assertEqual(result, {"backend": "inline"})
        run_job.assert_called_once_with(7, 3, 11, {"quantity": 1})

    @override_settings(CONTENT_AGENT_QUEUE_BACKEND="inline")
    @patch(
        "ai_content_agent.jobs.run_post_image_generation_job",
        return_value=True,
    )
    def test_inline_backend_runs_job_without_qstash_configuration(self, run_job):
        result = enqueue_post_image_generation(7, 11)

        self.assertEqual(result, {"backend": "inline"})
        run_job.assert_called_once_with(7, 11)

    @override_settings(CONTENT_AGENT_QUEUE_BACKEND="inline")
    @patch(
        "ai_content_agent.jobs.run_post_image_generation_job",
        return_value=False,
    )
    def test_inline_backend_raises_saved_job_error(self, run_job):
        user = create_user()
        batch = create_batch(user=user, error_message="OpenAI image edit failed")

        with self.assertRaisesMessage(RuntimeError, "OpenAI image edit failed"):
            enqueue_post_image_generation(user.id, batch.id)

        run_job.assert_called_once_with(user.id, batch.id)

    @override_settings(CONTENT_AGENT_QUEUE_BACKEND="unknown")
    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            enqueue_post_image_generation(7, 11)


@override_settings(CONTENT_AGENT_JOB_TOKEN="job-secret")
class QStashWorkerViewTest(APITestCase):
    def test_generation_worker_rejects_unauthenticated_request(self):
        response = self.client.post(
            reverse("post-generation-job"),
            {"user_id": 7, "brand_id": 3, "batch_id": 11, "data": {}},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    @patch(
        "ai_content_agent.views.run_post_generation_job",
        return_value=True,
    )
    def test_generation_worker_processes_authenticated_job(self, run_job):
        response = self.client.post(
            reverse("post-generation-job"),
            {
                "user_id": 7,
                "brand_id": 3,
                "batch_id": 11,
                "data": {"quantity": 1},
            },
            format="json",
            HTTP_X_CONTENT_AGENT_JOB_TOKEN="job-secret",
        )

        self.assertEqual(response.status_code, 200)
        run_job.assert_called_once_with(7, 3, 11, {"quantity": 1})

    @patch(
        "ai_content_agent.views.run_post_generation_job",
        return_value=False,
    )
    def test_generation_worker_returns_error_so_qstash_can_retry(self, _run_job):
        response = self.client.post(
            reverse("post-generation-job"),
            {
                "user_id": 7,
                "brand_id": 3,
                "batch_id": 11,
                "data": {"quantity": 1},
            },
            format="json",
            HTTP_X_CONTENT_AGENT_JOB_TOKEN="job-secret",
        )

        self.assertEqual(response.status_code, 500)

    def test_worker_rejects_unauthenticated_request(self):
        response = self.client.post(
            reverse("post-image-generation-job"),
            {"user_id": 7, "batch_id": 11},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    @patch(
        "ai_content_agent.views.run_post_image_generation_job",
        return_value=True,
    )
    def test_worker_processes_authenticated_job(self, run_job):
        response = self.client.post(
            reverse("post-image-generation-job"),
            {"user_id": 7, "batch_id": 11},
            format="json",
            HTTP_X_CONTENT_AGENT_JOB_TOKEN="job-secret",
        )

        self.assertEqual(response.status_code, 200)
        run_job.assert_called_once_with(7, 11)

    @patch(
        "ai_content_agent.views.run_post_image_generation_job",
        return_value=False,
    )
    def test_worker_returns_error_so_qstash_can_retry(self, _run_job):
        response = self.client.post(
            reverse("post-image-generation-job"),
            {"user_id": 7, "batch_id": 11},
            format="json",
            HTTP_X_CONTENT_AGENT_JOB_TOKEN="job-secret",
        )

        self.assertEqual(response.status_code, 500)

    def test_brand_visual_identity_worker_rejects_unauthenticated_request(self):
        response = self.client.post(
            reverse("brand-visual-identity-job"),
            {"user_id": 7, "brand_id": 3},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    @patch(
        "ai_content_agent.views.run_brand_visual_identity_job",
        return_value=True,
    )
    def test_brand_visual_identity_worker_processes_authenticated_job(self, run_job):
        response = self.client.post(
            reverse("brand-visual-identity-job"),
            {"user_id": 7, "brand_id": 3},
            format="json",
            HTTP_X_CONTENT_AGENT_JOB_TOKEN="job-secret",
        )

        self.assertEqual(response.status_code, 200)
        run_job.assert_called_once_with(7, 3)

    @patch(
        "ai_content_agent.views.run_brand_visual_identity_job",
        return_value=False,
    )
    def test_brand_visual_identity_worker_returns_error_for_retry(self, _run_job):
        response = self.client.post(
            reverse("brand-visual-identity-job"),
            {"user_id": 7, "brand_id": 3},
            format="json",
            HTTP_X_CONTENT_AGENT_JOB_TOKEN="job-secret",
        )

        self.assertEqual(response.status_code, 500)
