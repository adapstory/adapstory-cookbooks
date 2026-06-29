import unittest

from scripts.fetch_productframework import (
    canonicalize_external_url,
    clean_text_chunks,
    page_slug,
    title_to_slug,
)


class FetchProductFrameworkTests(unittest.TestCase):
    def test_page_slug_home(self) -> None:
        self.assertEqual(page_slug("https://productframework.ru/"), "home")

    def test_page_slug_nested_path(self) -> None:
        self.assertEqual(
            page_slug("https://productframework.ru/activities/customer_research"),
            "activities/customer_research",
        )

    def test_title_to_slug(self) -> None:
        self.assertEqual(
            title_to_slug("Product Architecture Framework"),
            "product-architecture-framework",
        )

    def test_clean_text_chunks_skips_duplicates_and_noise(self) -> None:
        chunks = clean_text_chunks(
            [
                "Гипотезы и эксперименты",
                "Полезный текст",
                "Полезный текст",
                "На сайте используются Cookies для чего-то",
            ],
            title="Some Title",
            description="Some Description",
        )
        self.assertEqual(chunks, ["Полезный текст"])

    def test_canonicalize_external_url(self) -> None:
        self.assertEqual(
            canonicalize_external_url(
                "https://miro.com/app/board/uXjVPLzO7IM=/?share_link_id=45726297278"
            ),
            "https://miro.com/app/board/uXjVPLzO7IM=/",
        )


if __name__ == "__main__":
    unittest.main()
