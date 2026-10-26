import unittest
from scripts.cliprausch.media import ass_subtitles, validate_words, draft_word_timings, asr_word
from types import SimpleNamespace

class MediaTests(unittest.TestCase):
    def test_zero_duration_words_share_neighbour_cue_without_losing_text_or_uncertainty(self):
        words,uncertain=draft_word_timings([
            {'start':.04,'end':.04,'text':'war','probability':.29},
            {'start':.04,'end':.3,'text':'es','probability':.95},
            {'start':.3,'end':.3,'text':'doch','probability':.8}],15)
        self.assertEqual(words[0]['text'],'war es doch')
        self.assertEqual((words[0]['start'],words[0]['end']),(.04,.3))
        self.assertEqual(words[0]['probability'],.29)
        self.assertEqual(uncertain,[0])
        self.assertIn('war es doch',ass_subtitles([{k:v for k,v in w.items() if k!='probability'} for w in words],15))

    def test_zero_duration_group_cannot_borrow_time_across_a_gap_or_without_speech(self):
        for words in ([{'start':0,'end':0,'text':'x'}],
                      [{'start':0,'end':0,'text':'x'},{'start':1,'end':2,'text':'y'}]):
            with self.assertRaises(ValueError):draft_word_timings(words,15)

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

    def test_uncertain_words_can_be_previewed_without_claiming_verified_text(self):
        words,uncertain=draft_word_timings([{'start':.1,'end':.6,'text':'Hallo','probability':.4},
            {'start':.59,'end':1.0,'text':'Leute','probability':.9}],15)
        self.assertEqual(uncertain,[0])
        self.assertEqual(words[0]['probability'],.4)
        self.assertEqual(words[1]['start'],.6)
        with self.assertRaises(ValueError):validate_words(words,15)
        self.assertIn('Hallo',ass_subtitles([{k:v for k,v in w.items() if k!='probability'} for w in words],15))

    def test_model_scalar_timestamps_are_converted_at_asr_boundary(self):
        class ModelScalar(float):pass
        word=SimpleNamespace(start=ModelScalar(.1),end=ModelScalar(.6),word=' Hallo ',probability=ModelScalar(.9))
        row=asr_word(word)
        self.assertIs(type(row['start']),float)
        self.assertIs(type(row['end']),float)
        self.assertIs(type(row['probability']),float)
        self.assertEqual(validate_words([row],15),[row])

if __name__=='__main__':unittest.main()
