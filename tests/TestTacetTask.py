import unittest
from unittest.mock import patch

import numpy as np
from ok.feature.Box import relative_box

from src.task.BaseWWTask import BaseWWTask
from src.task.TacetTask import TacetTask


class TestTacetTaskTeleport(unittest.TestCase):

    def make_task(self):
        task = TacetTask.__new__(TacetTask)
        task.structure = [4, 5, 5, 7]
        task.total_number = sum(task.structure)
        task.info_set = lambda *args, **kwargs: None
        task.log_info = lambda *args, **kwargs: None
        task.click_on_book_target = lambda serial, total, structure=None: True
        task._travel_feature = 'team_close'
        task.wait_click_feature = lambda *args, **kwargs: True
        task.is_fast_travel_unavailable = lambda: False
        task.back = lambda *args, **kwargs: None
        task.wait_in_team_and_world = lambda *args, **kwargs: True
        return task

    def test_direct_team_entry_keeps_the_travel_feature(self):
        task = self.make_task()

        self.assertTrue(task.teleport_to_tacet(0))
        self.assertEqual('team_close', task._travel_feature)

    def test_unreachable_target_is_skipped_instead_of_raising(self):
        # 日常任务里这一路抛错会把后面的领奖全部中断
        task = self.make_task()
        backs = []
        world_waits = []
        task.click_on_book_target = lambda serial, total, structure=None: False
        task.back = lambda *args, **kwargs: backs.append(kwargs)
        task.wait_in_team_and_world = lambda *args, **kwargs: world_waits.append(kwargs) or False

        self.assertFalse(task.teleport_to_tacet(0))
        self.assertEqual([{'after_sleep': 1}], backs)
        self.assertEqual([{'time_out': 10, 'raise_if_not_found': False, 'esc': True}], world_waits)

    def test_travel_button_path_also_clicks_fast_travel_before_team_screen(self):
        task = self.make_task()
        task.click_on_book_target = lambda serial, total, structure=None: (setattr(task, '_travel_feature',
                                                                                    'fast_travel_custom') or True)
        clicks = []
        task.wait_click_feature = lambda *args, **kwargs: clicks.append((args, kwargs)) or True

        self.assertTrue(task.teleport_to_tacet(1))
        self.assertEqual((('fast_travel_custom',), {'raise_if_not_found': False, 'time_out': 5,
                                                    'click_after_delay': 0.5, 'after_sleep': 1}), clicks[0])

    def test_travel_button_path_is_skipped_when_beacon_became_unreachable(self):
        task = self.make_task()
        task.click_on_book_target = lambda serial, total, structure=None: (setattr(task, '_travel_feature',
                                                                                    'fast_travel_custom') or True)
        task.is_fast_travel_unavailable = lambda: True
        means_of_escape = []
        task.back = lambda *args, **kwargs: means_of_escape.append(('back', kwargs))
        task.wait_in_team_and_world = lambda *args, **kwargs: means_of_escape.append(
            ('wait', kwargs)) or True

        self.assertFalse(task.teleport_to_tacet(1))
        self.assertEqual([('back', {'after_sleep': 1}),
                          ('wait', {'time_out': 10, 'raise_if_not_found': False, 'esc': False})],
                         means_of_escape)

    def test_out_of_range_index_still_raises(self):
        task = self.make_task()
        with self.assertRaises(IndexError):
            task.teleport_to_tacet(task.total_number)


class TestBaseWWTaskTravelUnavailable(unittest.TestCase):

    def test_fast_travel_unavailable_detects_red_warning_bar(self):
        width, height = 1280, 720
        task = BaseWWTask.__new__(BaseWWTask)
        frame = np.full((height, width, 3), (164, 165, 165), dtype=np.uint8)
        # 出现残象缩略图上的小红块不应被当成警告条
        frame[int(0.74 * height):int(0.78 * height), int(0.70 * width):int(0.72 * width)] = (80, 80, 190)
        task.box_of_screen = lambda x, y, to_x=1.0, to_y=1.0, **kwargs: relative_box(
            width, height, x, y, to_x=to_x, to_y=to_y, **kwargs)
        task.width_of_screen = lambda percent: round(percent * width)
        task.height_of_screen = lambda percent: round(percent * height)

        with patch.object(BaseWWTask, 'frame', frame):
            self.assertFalse(task.is_fast_travel_unavailable())

            frame[int(0.8465 * height):int(0.8861 * height), int(0.6875 * width):int(0.977 * width)] = (96, 96, 192)

            self.assertTrue(task.is_fast_travel_unavailable())


if __name__ == '__main__':
    unittest.main()
