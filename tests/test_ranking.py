import unittest

from radar.models import RawItem
from radar.ranking import deduplicate, rank


def config():
    return {
        "people": {"people": [{"name": "Ada Example", "aliases": ["Ada Example"], "priority": "high"}], "institutions": [{"name": "Example Institute", "aliases": ["Example Institute"], "priority": "high"}]},
        "topics": {"topics": [{"name": "VLA", "keywords": ["vision-language-action", "VLA"], "priority": "high"}], "negative_topics": ["funding round"]},
        "questions": {"questions": [{"question": "Does VLA need RL?", "keywords": ["VLA", "reinforcement learning"], "priority": "high"}]},
        "feedback": {"feedback": []},
    }


class RankingTests(unittest.TestCase):
    def test_ranking_rewards_evidence_and_entity_matches(self):
        item = RawItem("a", "https://arxiv.org/abs/1", "VLA reinforcement learning", "arxiv", "paper", authors_or_guests=["Ada Example"], raw_text="Example Institute studies vision-language-action models with reinforcement learning on real robots.")
        result = rank([item], config())
        self.assertGreaterEqual(result[0].score, 70)
        self.assertEqual(result[0].matched_people, ["Ada Example"])
        self.assertEqual(result[0].matched_topics, ["VLA"])

    def test_negative_content_is_excluded(self):
        item = RawItem("a", "https://example.com", "VLA funding round", "news", "blog", raw_text="A funding round about VLA")
        self.assertEqual(rank([item], config()), [])

    def test_deduplicate_prefers_original_over_aggregator(self):
        aggregator = RawItem("a", "https://aggregator.example/a", "New robot policy", "tea", "aggregator")
        original = RawItem("b", "https://lab.example/a", "New robot policy", "lab", "paper")
        self.assertEqual(deduplicate([aggregator, original]), [original])
