import unittest
from scripts.cliprausch.media import ass_subtitles, validate_words

class MediaTests(unittest.TestCase):
    def test_current_word_highlight_preserves_phrase_and_sanitizes_ass(self):
        text=ass_subtitles([{'start':0.2,'end':0.6,'text':'Was'},
            {'start':0.7,'end':1.1,'text':'ein'}, {'start':1.15,'end':1.8,'text':'{Clutch}!'}],15)
        self.assertIn('PlayResX: 1080',text)
        self.assertEqual(text.count('Dialogue:'),3)
        self.assertIn('Was',text)
        self.assertNotIn('{Clutch}',text)
        self.assertIn(r'\1c&HFFFF00&',text)

    def test_overlap_outside_clip_and_uncertain_words_are_rejected(self):
        for words in ([{'start':1,'end':2,'text':'hey','probability':.1}],
                      [{'start':-1,'end':2,'text':'hey'}],
                      [{'start':1,'end':16,'text':'hey'}],
                      [{'start':1,'end':2,'text':'x'*90}], []):
            with self.assertRaises(ValueError):validate_words(words,15)

if __name__=='__main__':unittest.main()
