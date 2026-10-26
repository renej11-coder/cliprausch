import unittest
from scripts.cliprausch.captions import existing_caption_line,decide
class CaptionDetectionTests(unittest.TestCase):
    def test_small_source_caption_crop_maps_back_to_source_coordinates(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from scripts.cliprausch.captions import ocr_lines
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'frame.png';path.write_bytes(b'frame')
            def crop(args):Path(args[-1]).write_bytes(b'crop')
            with patch('scripts.cliprausch.captions.command',side_effect=crop),patch(
                'scripts.cliprausch.captions.read_ocr',side_effect=[[],[
                    {'text':'Gegner so langsam','confidence':95,'cx':.5,'cy':.8}]]):
                lines=ocr_lines(path,1600,900)
            self.assertAlmostEqual(lines[0]['cx'],.5)
            self.assertTrue(existing_caption_line(lines[0],'kommen gute gegner'))
            self.assertFalse(path.with_suffix('.crop.png').exists())

    def test_nooreax_original_subtitle_is_detected(self):
        line={'text':'so viel Zeit','confidence':91,'cx':.5,'cy':.93}
        self.assertTrue(existing_caption_line(line,'wir hatten so viel zeit'))
    def test_bottom_caption_shape_is_conservatively_preserved_even_with_asr_error(self):
        self.assertTrue(existing_caption_line({'text':'Wir hatten sogar','confidence':82,'cx':.5,'cy':.9},'wir haetten gesagt'))
    def test_chat_and_menu_labels_do_not_trigger_caption_shape_rule(self):
        for line in ({'text':'Title Screen','confidence':90,'cx':.5,'cy':.5},
                     {'text':'HAHA was passiert','confidence':90,'cx':.94,'cy':.85}):
            self.assertFalse(existing_caption_line(line,'so viel zeit'))
    def test_no_added_track_when_existing_caption_found(self):
        self.assertEqual(decide(True,True),'source_preserved')
        self.assertEqual(decide(False,True),'word_highlight')
    def test_incomplete_scan_cannot_add_a_track(self):
        with self.assertRaises(ValueError):decide(False,False)

    def test_render_filter_adds_exactly_one_track_or_preserves_source_only(self):
        from scripts.cliprausch.media import video_filter
        self.assertEqual(video_filter(True).count('ass=subs.ass'),1)
        self.assertNotIn('ass=',video_filter(False))
        self.assertIn('drawbox=',video_filter(False))

    def test_automatic_receipt_rejects_missing_scan_and_duplicate_track_evidence(self):
        from scripts.cliprausch.automatic import receipt
        from test_core import config,item
        row=item();words=[{'start':.2,'end':.8,'text':'Hallo','probability':.9}]
        qa=dict(row,video_codec='h264',audio_codec='aac',full_decode=True,headline=False,
            subtitle_mode='source_preserved',uncertain_segments=[],uncertain_word_indexes=[],added_caption_tracks=0)
        with self.assertRaises(ValueError):receipt(config(),row,qa,words)
        qa['subtitle_scan']={'policy_version':4,'method':'tesseract_deu_eng_v1','complete':True,
            'source_sha256':row['source_sha256'],'decision':'source_preserved','detected':True,
            'frames_scanned':3,'planned_frames':30,'added_caption_tracks':0}
        self.assertEqual(receipt(config(),row,qa,words)['subtitle_mode'],'source_preserved')
        qa['added_caption_tracks']=1
        with self.assertRaises(ValueError):receipt(config(),row,qa,words)

    def test_existing_single_word_dynamic_caption_is_preserved(self):
        self.assertTrue(existing_caption_line({'text':'NEIN!','confidence':98,'cx':.5,'cy':.9},'nein'))
        self.assertTrue(existing_caption_line({'text':'JA!','confidence':95,'cx':.5,'cy':.9},'anderer asr text'))
        self.assertFalse(existing_caption_line({'text':'74','confidence':99,'cx':.5,'cy':.9},'74'))

    def test_scan_prefers_real_speech_caption_over_earlier_possible_gui_text(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from scripts.cliprausch.captions import scan
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.mp4';source.write_bytes(b'fake-source')
            def frames(args):
                root=Path(args[-1]).parent
                for i in range(3):(root/f'{i:04d}.png').write_bytes(b'image')
            lines=[[{'text':'Firework Rocket','confidence':90,'cx':.5,'cy':.9}],[],
                [{'text':'so viel Zeit','confidence':95,'cx':.5,'cy':.94}]]
            with patch('scripts.cliprausch.captions.command',side_effect=frames),patch('scripts.cliprausch.captions.ocr_lines',side_effect=lines):
                report=scan(source,{'width':1280,'height':720,'duration':1.5},[{'start':1,'end':1.5,'text':'so viel Zeit'}])
            self.assertEqual(report['matched_text'],'so viel Zeit')
            self.assertEqual(report['match_kind'],'speech_match')
            self.assertEqual(report['frames_scanned'],3)
            self.assertEqual(report['added_caption_tracks'],0)
    def test_missing_ocr_tool_stops_before_rendering(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from scripts.cliprausch.captions import scan
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.mp4';source.write_bytes(b'fake-source')
            def frames(args):(Path(args[-1]).parent/'0001.png').write_bytes(b'image')
            with patch('scripts.cliprausch.captions.command',side_effect=frames),patch('scripts.cliprausch.captions.ocr_lines',side_effect=FileNotFoundError):
                with self.assertRaisesRegex(ValueError,'subtitle_scan_failed'):
                    scan(source,{'width':1280,'height':720,'duration':.5},[])
