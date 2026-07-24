from django.test import TestCase
from collections import Counter

from resume.ml.preprocessing import (
    simple_stem,
    tokenize,
    vectorize_tokens,
    combine_feature_text,
)


class SimpleStemTests(TestCase):

    def test_removes_ing(self):
        self.assertEqual(simple_stem("testing"), "test")

    def test_removes_ed(self):
        self.assertEqual(simple_stem("worked"), "work")

    def test_removes_plural_s(self):
        self.assertEqual(simple_stem("developers"), "developer")

    def test_does_not_modify_short_word(self):
        self.assertEqual(simple_stem("go"), "go")


class TokenizeTests(TestCase):

    def test_lowercases_text(self):
        tokens = tokenize("Python DJANGO")
        self.assertEqual(tokens, ["python", "django"])

    def test_removes_stopwords(self):
        tokens = tokenize("This is a python developer")
        self.assertEqual(tokens, ["python", "developer"])

    def test_keeps_special_tokens(self):
        tokens = tokenize("C++ C# Python")
        self.assertIn("c++", tokens)
        self.assertIn("c#", tokens)
        self.assertIn("python", tokens)

    def test_removes_punctuation(self):
        tokens = tokenize("Python, Django! REST API.")
        self.assertEqual(tokens, ["python", "django", "rest", "api"])

    def test_applies_stemming(self):
        tokens = tokenize("testing developed")
        self.assertEqual(tokens, ["test", "develop"])

    def test_removes_single_character_tokens(self):
        tokens = tokenize("a b c python")
        self.assertEqual(tokens, ["python"])

    def test_empty_string(self):
        self.assertEqual(tokenize(""), [])


class VectorizeTests(TestCase):

    def test_counts_tokens(self):
        tokens = ["python", "python", "django"]

        vector = vectorize_tokens(tokens)

        expected = Counter({
            "python": 2,
            "django": 1,
        })

        self.assertEqual(vector, expected)

    def test_empty_tokens(self):
        self.assertEqual(vectorize_tokens([]), Counter())


class CombineFeatureTextTests(TestCase):

    def test_combines_all_fields(self):

        text = combine_feature_text(
            resume_text="Python Developer",
            skills="Python, Django",
            education="BSc Computer Science",
            experience="Software Engineer"
        )

        self.assertIn("Python Developer", text)
        self.assertIn("Python, Django", text)
        self.assertIn("BSc Computer Science", text)
        self.assertIn("Software Engineer", text)

    def test_skill_weighting(self):

        text = combine_feature_text(
            resume_text="",
            skills="Python",
        )

        self.assertEqual(text, "Python Python Python")

    def test_experience_weighting(self):

        text = combine_feature_text(
            resume_text="",
            experience="QA Engineer"
        )

        self.assertEqual(text, "QA Engineer QA Engineer")

    def test_only_resume_text(self):

        text = combine_feature_text(
            resume_text="Machine Learning Engineer"
        )

        self.assertEqual(text, "Machine Learning Engineer")

    def test_empty_fields(self):

        text = combine_feature_text(
            resume_text="",
            skills="",
            education="",
            experience=""
        )

        self.assertEqual(text, "")