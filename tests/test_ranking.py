import unittest

from radar.models import RawItem
from radar.ranking import deduplicate, rank


def config():
    return {
        "people": {
            "people": [{"name": "Ada Example", "aliases": ["Ada Example"], "priority": "high"}],
            "institutions": [{"name": "Example Institute", "aliases": ["Example Institute"], "priority": "high"}],
        },
        "topics": {
            "topics": [{"name": "Robot Learning", "keywords": ["robot learning", "manipulation"], "priority": "high"}],
            "negative_topics": ["funding round"],
        },
        "questions": {
            "questions": [
                {
                    "question": "Does robot learning benefit from feedback?",
                    "keywords": ["robot learning", "feedback"],
                    "priority": "high",
                }
            ]
        },
        "feedback": {"feedback": []},
    }


class RankingTests(unittest.TestCase):
    def test_ranking_rewards_evidence_and_entity_matches(self):
        item = RawItem(
            "a",
            "https://arxiv.org/abs/1",
            "Robot learning with feedback",
            "arxiv",
            "paper",
            authors_or_guests=["Ada Example"],
            raw_text="Example Institute studies robot learning with feedback on manipulation tasks.",
        )
        result = rank([item], config())
        self.assertGreaterEqual(result[0].score, 70)
        self.assertEqual(result[0].matched_people, ["Ada Example"])
        self.assertEqual(result[0].matched_topics, ["Robot Learning"])

    def test_negative_content_is_excluded(self):
        item = RawItem(
            "a",
            "https://example.com",
            "Robot learning funding round",
            "news",
            "blog",
            raw_text="A funding round about robot learning",
        )
        self.assertEqual(rank([item], config()), [])

    def test_deduplicate_prefers_original_over_aggregator(self):
        aggregator = RawItem("a", "https://aggregator.example/a", "New robot policy", "tea", "aggregator")
        original = RawItem("b", "https://lab.example/a", "New robot policy", "lab", "paper")
        self.assertEqual(deduplicate([aggregator, original]), [original])
