from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase, override_settings

from ai_core.clients import _build_image_generation_prompt, _edit_image_bytes
from ai_core.clients import _get_image_format_config
from ai_core.clients import _get_replicate_merge_image_aspect_ratio
from ai_core.prompts import (
    build_user_background_replace_prompt,
    build_post_plan_prompt,
    build_posts_from_plan_prompt,
    build_user_image_edit_prompt,
)
from ai_core.prompts.registry import PROMPT_SETS, get_prompt_set


class PromptQualityTestCase(SimpleTestCase):
    def get_data(self):
        return {
            "quantity": 2,
            "business_name": "UpFit Gym",
            "niche": "academia",
            "objective": "atrair alunos",
            "tone": "motivacional",
            "theme": "volta a rotina fitness",
            "brand_visual_identity": "visual moderno com verde como acento",
        }

    def test_plan_prompt_prioritizes_theme_and_visual_variety(self):
        prompt = build_post_plan_prompt(self.get_data())

        self.assertIn("tema/campanha principal deve guiar", prompt)
        self.assertIn("substancialmente diferente", prompt)
        self.assertIn("cena, sujeito principal, composição", prompt)

    def test_english_brand_uses_english_content_rules(self):
        data = self.get_data()
        data["content_language"] = "en-US"

        plan_prompt = build_post_plan_prompt(data)
        image_prompt = _build_image_generation_prompt(
            "A customer using the product",
            content_language="en-US",
        )

        self.assertIn("Respond in natural American English", plan_prompt)
        self.assertIn("use only short English words", image_prompt)
        self.assertIn("not write in Portuguese", image_prompt)

    def test_prompt_sets_expose_the_same_complete_interface(self):
        required_builders = {
            "build_post_plan_prompt",
            "build_post_from_idea_prompt",
            "build_posts_from_plan_prompt",
            "build_post_prompt",
            "build_brand_visual_identity_prompt",
            "build_image_generation_prompt",
            "build_user_image_edit_prompt",
            "build_user_background_replace_prompt",
            "build_user_merge_images_prompt",
        }

        for language, prompt_set in PROMPT_SETS.items():
            with self.subTest(language=language):
                for builder in required_builders:
                    self.assertTrue(callable(getattr(prompt_set, builder)))

        self.assertIs(get_prompt_set("unsupported"), PROMPT_SETS["pt-BR"])

    def test_english_prompt_has_no_portuguese_instruction_scaffold(self):
        data = {
            **self.get_data(),
            "content_language": "en-US",
            "niche": "fitness center",
            "objective": "attract new members",
            "tone": "motivational",
            "theme": "back to fitness",
            "brand_visual_identity": "modern look with green accents",
        }
        prompt = build_post_plan_prompt(data)

        for portuguese_instruction in (
            "Negócio:",
            "Objetivo geral:",
            "Regras:",
            "Responda em",
            "Retorne exatamente",
        ):
            self.assertNotIn(portuguese_instruction, prompt)

    def test_batch_prompt_requires_specific_non_interchangeable_image_prompts(self):
        prompt = build_posts_from_plan_prompt(
            self.get_data(),
            [
                {
                    "title": "Post 1",
                    "theme": "Rotina",
                    "objective": "Atrair",
                    "format": "educativo",
                    "angle": "Recomeco",
                    "visual_direction": "Pessoa preparando mochila de treino",
                },
                {
                    "title": "Post 2",
                    "theme": "Treino",
                    "objective": "Converter",
                    "format": "oferta",
                    "angle": "Aula experimental",
                    "visual_direction": "Recepcao da academia com convite",
                },
            ],
        )

        self.assertIn("Não produza prompts visuais intercambiáveis", prompt)
        self.assertIn("sujeito principal da imagem", prompt)
        self.assertIn("detalhes concretos do tema", prompt)

    def test_image_generation_prompt_avoids_generic_stock_style(self):
        prompt = _build_image_generation_prompt(
            "Aluno amarrando tenis antes do treino matinal"
        )

        self.assertIn("não uma imagem genérica de banco", prompt)
        self.assertIn("Evite a fórmula visual", prompt)
        self.assertIn("situações de uso relevantes ao tema", prompt)

    def test_image_generation_prompt_can_request_portrait_format(self):
        prompt = _build_image_generation_prompt(
            "Aluno amarrando tenis antes do treino matinal",
            image_format="portrait",
        )

        self.assertIn("vertical em formato retrato", prompt)

    def test_replicate_merge_image_uses_instagram_friendly_aspect_ratios(self):
        self.assertEqual(
            _get_replicate_merge_image_aspect_ratio(
                _get_image_format_config("square"),
            ),
            "1:1",
        )
        self.assertEqual(
            _get_replicate_merge_image_aspect_ratio(
                _get_image_format_config("portrait"),
            ),
            "4:5",
        )
        self.assertEqual(
            _get_replicate_merge_image_aspect_ratio(
                _get_image_format_config("landscape"),
            ),
            "16:9",
        )

    def test_user_image_edit_prompt_prioritizes_original_identity(self):
        prompt = build_user_image_edit_prompt(
            "Melhore a luz",
            "visual moderno com verde como acento",
        )

        self.assertIn("modo conservador", prompt)
        self.assertIn("Nao recrie a foto do zero", prompt)
        self.assertIn("a pessoa em outra pessoa", prompt)
        self.assertIn("Altere somente o fundo", prompt)
        self.assertIn("Nao edite rosto", prompt)
        self.assertIn("preserve a imagem original", prompt)

    def test_background_replace_prompt_prioritizes_user_requested_background(self):
        prompt = build_user_background_replace_prompt(
            "Jardim de flores azuis",
            {
                "title": "Oferta premium",
                "theme": "Servico exclusivo",
                "objective": "Converter",
                "format": "oferta",
                "angle": "Ambiente sofisticado",
                "visual_direction": "Recepcao moderna com detalhes dourados",
            },
            "Pessoa em uma recepcao de clinica premium",
            "visual moderno com verde como acento",
        )

        self.assertIn("Jardim de flores azuis", prompt)
        self.assertIn("fonte principal de verdade", prompt)
        self.assertIn("Nao substitua o fundo solicitado", prompt)
        self.assertNotIn("Recepcao moderna", prompt)
        self.assertNotIn("Pessoa em uma recepcao", prompt)

    def test_prompts_hide_empty_brand_visual_identity(self):
        data = self.get_data()
        data["brand_visual_identity"] = ""

        plan_prompt = build_post_plan_prompt(data)
        edit_prompt = build_user_image_edit_prompt("Melhore a luz", "")

        self.assertNotIn("Identidade visual da marca:", plan_prompt)
        self.assertNotIn("Identidade visual da marca:", edit_prompt)
        self.assertIn("Pedido do usuario:", edit_prompt)
        self.assertIn("Instrucoes obrigatorias:", edit_prompt)

    @override_settings(
        MEDIA_ROOT="/tmp",
        FAL_KEY="test-key",
        FAL_QUEUE_BASE_URL="https://queue.fal.run",
        FAL_IMAGE_EDIT_MODEL="fal-ai/flux-pro/kontext",
        FAL_IMAGE_EDIT_ENHANCE_PROMPT=True,
        FAL_IMAGE_EDIT_ASPECT_RATIO="",
        FAL_IMAGE_EDIT_SEED="123456",
        FAL_IMAGE_EDIT_GUIDANCE_SCALE=3.5,
        FAL_IMAGE_EDIT_SAFETY_TOLERANCE="5",
        FAL_IMAGE_EDIT_POLL_INTERVAL_SECONDS=0,
        FAL_IMAGE_EDIT_TIMEOUT_SECONDS=10,
    )
    @patch("ai_core.clients.requests.get")
    @patch("ai_core.clients.requests.post")
    @patch("ai_core.clients._upload_fal_image")
    @patch("ai_core.clients._prepare_image_edit_source")
    def test_image_edit_uses_flux_kontext_pro(
        self,
        prepare_source,
        upload_fal_image,
        post,
        get,
    ):
        source_path = MagicMock()
        source_file = Mock()
        source_file.read.return_value = b"source"
        source_path.open.return_value.__enter__.return_value = source_file
        prepare_source.return_value = source_path
        upload_fal_image.return_value = "https://v3.fal.media/files/source.png"
        post.return_value.json.return_value = {
            "request_id": "request-id",
            "status_url": "https://queue.fal.run/fal-ai/flux-pro/kontext/requests/request-id/status",
            "response_url": "https://queue.fal.run/fal-ai/flux-pro/kontext/requests/request-id/response",
        }
        get.side_effect = [
            SimpleNamespace(
                raise_for_status=Mock(),
                json=Mock(
                    return_value={
                        "status": "COMPLETED",
                        "response_url": "https://queue.fal.run/fal-ai/flux-pro/kontext/requests/request-id/response",
                    }
                ),
            ),
            SimpleNamespace(
                raise_for_status=Mock(),
                json=Mock(
                    return_value={
                        "images": [
                            {"url": "https://v3.fal.media/files/result.png"}
                        ],
                        "prompt": "Preserve person and improve lighting",
                    }
                ),
            ),
            SimpleNamespace(
                raise_for_status=Mock(),
                content=b"image",
            ),
        ]

        image_bytes = _edit_image_bytes(
            Path("/tmp/source.png"),
            "Preserve person and improve lighting",
            image_format="portrait",
        )

        self.assertEqual(image_bytes, b"image")
        post.assert_called_once()
        post_payload = post.call_args.kwargs["json"]
        self.assertEqual(
            post.call_args.args[0],
            "https://queue.fal.run/fal-ai/flux-pro/kontext",
        )
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Key test-key",
        )
        upload_fal_image.assert_called_once_with(b"source", "image/png")
        self.assertEqual(post_payload["prompt"], "Preserve person and improve lighting")
        self.assertEqual(post_payload["image_url"], "https://v3.fal.media/files/source.png")
        self.assertNotIn("aspect_ratio", post_payload)
        self.assertEqual(post_payload["output_format"], "png")
        self.assertEqual(post_payload["guidance_scale"], 3.5)
        self.assertEqual(post_payload["seed"], 123456)
        self.assertEqual(post_payload["num_images"], 1)
        self.assertIs(post_payload["enhance_prompt"], True)
        self.assertEqual(post_payload["safety_tolerance"], "5")
        self.assertEqual(
            get.call_args_list[0].args[0],
            post.return_value.json.return_value["status_url"],
        )
        self.assertEqual(
            get.call_args_list[1].args[0],
            post.return_value.json.return_value["response_url"],
        )
        self.assertEqual(get.call_args_list[2].args[0], "https://v3.fal.media/files/result.png")
        source_path.unlink.assert_called_once_with(missing_ok=True)

    @patch("ai_core.clients._replace_background_image_bytes")
    def test_image_edit_can_replace_background(self, replace_background):
        replace_background.return_value = b"composited"

        image_bytes = _edit_image_bytes(
            Path("/tmp/source.png"),
            "A clean studio background",
            image_format="portrait",
            image_edit_mode="background_replace",
        )

        self.assertEqual(image_bytes, b"composited")
        replace_background.assert_called_once()
        self.assertEqual(replace_background.call_args.args[0], Path("/tmp/source.png"))
        self.assertEqual(
            replace_background.call_args.args[1],
            "A clean studio background",
        )
        self.assertEqual(
            replace_background.call_args.args[2]["aspect_ratio"],
            "2:3",
        )

    @override_settings(
        MEDIA_ROOT="/tmp",
        REPLICATE_API_TOKEN="test-token",
        REPLICATE_MERGE_IMAGE_EDIT_MODEL="black-forest-labs/flux-2-pro",
        REPLICATE_MERGE_IMAGE_EDIT_SAFETY_TOLERANCE=4,
        REPLICATE_MERGE_IMAGE_EDIT_POLL_INTERVAL_SECONDS=0,
        REPLICATE_MERGE_IMAGE_EDIT_TIMEOUT_SECONDS=10,
    )
    @patch("ai_core.clients.requests.get")
    @patch("ai_core.clients.requests.post")
    @patch("ai_core.clients._build_image_data_url")
    @patch("ai_core.clients._prepare_image_edit_source")
    def test_image_edit_can_merge_three_images_with_replicate(
        self,
        prepare_source,
        build_data_url,
        post,
        get,
    ):
        source_path = MagicMock()
        reference_path = MagicMock()
        focus_path = MagicMock()
        prepare_source.side_effect = [source_path, reference_path, focus_path]
        build_data_url.side_effect = [
            "data:image/png;base64,source",
            "data:image/png;base64,reference",
            "data:image/png;base64,focus",
        ]
        post.return_value.json.return_value = {
            "urls": {
                "get": "https://api.replicate.com/v1/predictions/id",
            },
        }
        get.side_effect = [
            SimpleNamespace(
                raise_for_status=Mock(),
                json=Mock(
                    return_value={
                        "status": "succeeded",
                        "output": ["https://replicate.delivery/result.png"],
                    }
                ),
            ),
            SimpleNamespace(
                raise_for_status=Mock(),
                content=b"merged",
            ),
        ]

        image_bytes = _edit_image_bytes(
            Path("/tmp/source.png"),
            "Apply clothing from the second image",
            reference_image_path=Path("/tmp/reference.png"),
            focus_image_path=Path("/tmp/focus.png"),
            image_format="portrait",
            image_edit_mode="merge_images",
        )

        self.assertEqual(image_bytes, b"merged")
        self.assertEqual(
            post.call_args.args[0],
            "https://api.replicate.com/v1/models/black-forest-labs/flux-2-pro/predictions",
        )
        payload = post.call_args.kwargs["json"]["input"]
        self.assertEqual(
            payload["input_images"],
            [
                "data:image/png;base64,source",
                "data:image/png;base64,reference",
                "data:image/png;base64,focus",
            ],
        )
        self.assertEqual(payload["safety_tolerance"], 4)
        self.assertEqual(payload["aspect_ratio"], "4:5")
        source_path.unlink.assert_called_once_with(missing_ok=True)
        reference_path.unlink.assert_called_once_with(missing_ok=True)
        focus_path.unlink.assert_called_once_with(missing_ok=True)

    @override_settings(
        FAL_KEY="test-key",
        FAL_QUEUE_BASE_URL="https://queue.fal.run",
        FAL_BACKGROUND_GENERATION_MODEL="fal-ai/flux-pro",
        FAL_IMAGE_EDIT_ENHANCE_PROMPT=True,
        FAL_IMAGE_EDIT_ASPECT_RATIO="",
        FAL_IMAGE_EDIT_SEED="123456",
        FAL_IMAGE_EDIT_GUIDANCE_SCALE=3.5,
        FAL_IMAGE_EDIT_SAFETY_TOLERANCE="5",
    )
    @patch("ai_core.clients.requests.post")
    def test_background_generation_uses_text_to_image_model(self, post):
        post.return_value.json.return_value = {
            "request_id": "request-id",
            "status_url": "https://queue.fal.run/fal-ai/flux-pro/requests/request-id/status",
            "response_url": "https://queue.fal.run/fal-ai/flux-pro/requests/request-id/response",
        }

        from ai_core.clients import _submit_flux_image_generation

        _submit_flux_image_generation("A clean studio background", {})

        self.assertEqual(
            post.call_args.args[0],
            "https://queue.fal.run/fal-ai/flux-pro",
        )
        self.assertNotIn("image_url", post.call_args.kwargs["json"])
