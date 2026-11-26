import json
import os
import sys
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bot  # noqa: E402


class R:
    def __init__(self, code, data):
        self.status_code, self._data, self.text = code, data, json.dumps(data)

    def json(self):
        return self._data


DRAFT = {"choice": 1, "quotes": [{"quote": "q", "speaker": "s", "real_source": "neu"}] * 6,
         "hooks": ["h"] * 5, "send_to": "Jemandem, der Formulare liebt", "comment_question": "Ja oder nein?",
         "teaser": "Endlich sagt es mal einer."}
FINAL = {"ok": True, "score": 9, "scores": [9, 5, 5, 5, 5, 5], "reason": "konkret", "hook": "Rate mal, wer das gesagt hat",
         "quote": "Bitte ziehen Sie eine Nummer und warten Sie.", "speaker": "Sisyphos, am Bürgeramt",
         "send_to": "jemandem, der Formulare liebt"}


def fake_llm(final):
    def llm(system, user):
        return dict(final) if "Schlussredaktion" in system else dict(DRAFT)
    return llm


def fake_feed(titles):
    now = time.gmtime()
    return lambda url: types.SimpleNamespace(entries=[
        {"title": f"{t} - Tagesschau", "link": f"https://example.org/{i}", "source": {"title": "Tagesschau"},
         "published_parsed": now} for i, t in enumerate(titles)])


class BotTests(unittest.TestCase):
    def setUp(self):
        self.state = []
        patches = [
            mock.patch.object(bot, "load_state", lambda: list(self.state)),
            mock.patch.object(bot, "render", lambda c, *a, **k: 12.0),
            mock.patch.object(bot, "save_json", lambda *a, **k: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_blocklist_catches_compounds_but_not_harmless_words(self):
        self.assertTrue(bot.blocked("Flugzeugabsturz in den Alpen"))
        self.assertTrue(bot.blocked("Unfallopfer gefunden"))
        self.assertFalse(bot.blocked("Neuer Prozessor vorgestellt"))
        self.assertFalse(bot.blocked("Brandenburg digitalisiert Ämter"))

    def test_german_quote_marks_and_dash(self):
        with mock.patch.object(bot, "llm", fake_llm(FINAL)), \
             mock.patch.object(bot.feedparser, "parse", fake_feed(["Bürgeramt: Wartezeit steigt auf zwölf Wochen"])):
            c = bot.build_joke(bot.CFG["topics"][2], bot.CFG["formats"][0], set(), [])
        self.assertEqual(c["setup"], "„Bitte ziehen Sie eine Nummer und warten Sie.“")
        self.assertEqual(c["punchline"], "– Sisyphos, am Bürgeramt")
        self.assertTrue(c["send_to"].startswith("jemandem"))

    def test_caption_has_satire_note_and_max_five_hashtags(self):
        with mock.patch.object(bot, "llm", fake_llm(FINAL)), \
             mock.patch.object(bot.feedparser, "parse", fake_feed(["Bürgeramt: Wartezeit steigt auf zwölf Wochen"])):
            c = bot.build_joke(bot.CFG["topics"][2], bot.CFG["formats"][0], set(), [])
        self.assertIn("Satire.", c["caption"])
        self.assertLessEqual(c["caption"].split("\n")[-1].count("#"), 5)
        self.assertNotIn("Sisyphos", c["caption"].split("\n")[0])  # Teaser verrät den Urheber nicht

    def test_low_score_is_rejected(self):
        weak = dict(FINAL, score=7, ok=True)
        with mock.patch.object(bot, "llm", fake_llm(weak)), \
             mock.patch.object(bot.feedparser, "parse", fake_feed(["Bürgeramt: Wartezeit steigt auf zwölf Wochen"])):
            self.assertIsNone(bot.build_joke(bot.CFG["topics"][2], bot.CFG["formats"][0], set(), []))

    def test_too_long_speaker_is_rejected(self):
        long_speaker = dict(FINAL, speaker="Johann Wolfgang von Goethe an einem verregneten Dienstag in Weimar beim Frühstück")
        self.assertFalse(bot.valid(long_speaker))
        self.assertTrue(bot.valid(dict(FINAL, setup=FINAL["quote"], punchline=FINAL["speaker"])))

    def test_blocked_headlines_and_seen_links_are_skipped(self):
        with mock.patch.object(bot.feedparser, "parse", fake_feed(["Schwerer Unfall auf der A9", "Bahn erfindet neue Ausrede"])):
            out = bot.fetch_candidates(bot.CFG["topics"][2], {"https://example.org/1"})
        self.assertEqual(out, [])

    def test_publish_refuses_wrong_account(self):
        env = {"GITHUB_REPOSITORY": "realbeardedman/witz-bot-de", "IG_USER_ID": "1", "IG_ACCESS_TOKEN": "t"}
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(bot.requests, "get", lambda *a, **k: R(200, {"username": "citation.needed.daily"})):
            with self.assertRaises(SystemExit) as cm:
                bot.publish_guard()
        self.assertIn("Falsches", str(cm.exception))

    def test_publish_refuses_other_repository(self):
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "realbeardedman/witz-bot"}):
            with self.assertRaises(SystemExit) as cm:
                bot.publish_guard()
        self.assertIn("nur im Repository", str(cm.exception))

    def test_publish_guard_accepts_correct_account(self):
        env = {"GITHUB_REPOSITORY": "realbeardedman/witz-bot-de", "IG_USER_ID": "1", "IG_ACCESS_TOKEN": "t",
               "IG_EXPECTED_USERNAME": "im.zweifel.goethe"}
        with mock.patch.dict(os.environ, env), \
             mock.patch.object(bot.requests, "get", lambda *a, **k: R(200, {"username": "im.zweifel.goethe"})):
            bot.publish_guard()

    def test_long_texts_fit_in_frame(self):
        c = {"date": "t", "headline": "Bundesagentur meldet: Antragsformular für die Digitalisierung von Antragsformularen jetzt nur noch auf Papier erhältlich",
             "source": "Süddeutsche Zeitung", "hook": "Das hätte niemand kommen sehen. Außer Kafka.",
             "setup": bot.quoted("Wir digitalisieren jetzt alles, bitte reichen Sie den Antrag dafür in dreifacher Ausfertigung per Fax beim zuständigen Amt ein."),
             "punchline": "– Franz Kafka, Sachbearbeiter seit 1912", "send_to": "jemandem, der noch ein Faxgerät besitzt"}
        L = bot.layout(c)
        self.assertLessEqual(L["punch_y"] + L["punch"].height, bot.MAIN_BOTTOM)

    def test_duplicate_quote_and_recent_speaker_are_rejected(self):
        history = [{"setup": "„Bitte ziehen Sie eine Nummer und warten Sie.“", "punchline": "– Noah, auf der Arche"}]
        self.assertIn("Zitat", bot.duplicate({"setup": "Bitte ziehen Sie eine Nummer, und warten Sie!", "punchline": "Kafka"}, history))
        self.assertIn("noah", bot.duplicate({"setup": "Neuer Satz", "punchline": "Noah, beim Packen"}, history))
        self.assertIsNone(bot.duplicate({"setup": "Neuer Satz", "punchline": "Sisyphos"}, history))

    def test_failed_reservation_posts_nothing(self):
        def failing_git(*args):
            raise bot.subprocess.CalledProcessError(1, "git")
        uploads = []
        with mock.patch.object(bot, "git", failing_git), \
             mock.patch.object(bot, "publish_reel", lambda *a: uploads.append(a) or "m1"):
            with self.assertRaises(SystemExit) as cm:
                bot.reserve({"date": "2026-12-01-0617", "headline": "h"})
        self.assertIn("Nichts gepostet", str(cm.exception))
        self.assertEqual(uploads, [])

    def test_reservation_then_publish_marks_entry(self):
        store = []
        with mock.patch.object(bot, "load_state", lambda: [dict(e) for e in store]), \
             mock.patch.object(bot, "save_json", lambda path, data: store.__setitem__(slice(None), data)), \
             mock.patch.object(bot, "git", lambda *a: None):
            i = bot.reserve({"date": "2026-12-01-0617", "headline": "h", "setup": "s", "punchline": "p"})
            self.assertEqual(store[i]["status"], "reserved")
            bot.record(i, "media42")
        self.assertEqual(store[i]["status"], "published")
        self.assertEqual(store[i]["media_id"], "media42")

    def test_instagram_errors_are_shortened(self):
        msg = bot.ig_error(R(400, {"error": {"code": 190, "error_subcode": 463, "message": "x" * 500}}))
        self.assertIn("Code 190/463", msg)
        self.assertLess(len(msg), 220)


class SendTargetTests(unittest.TestCase):
    def test_double_prefix_removed(self):
        self.assertEqual(bot.send_target("Schick das jemandem, der nur noch Pakete öffnet."),
                         "jemandem, der nur noch Pakete öffnet")

    def test_bad_start_falls_back(self):
        self.assertEqual(bot.send_target("Schick das an den Lichtsuchenden", "deiner Kollegin mit drei Abos"),
                         "deiner Kollegin mit drei Abos")
        self.assertEqual(bot.send_target("an den Lichtsuchenden"), bot.T_["default_send"])


if __name__ == "__main__":
    unittest.main()
