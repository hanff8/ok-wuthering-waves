import unittest

from src.task.BaseWWTask import BaseWWTask


class FakeMonthlyCardTask:
    """Drives BaseWWTask.handle_monthly_card without a real device.

    back_to_world simulates whether the click actually dismisses the popup and
    returns to the world; when it does not, the handler must not mark the card
    as handled (otherwise the caller's ensure_main budget gets consumed and
    raises "Please start in game world and in team!").
    """

    def __init__(self, card_found=True, back_to_world=False):
        self.card_found = card_found
        self.back_to_world = back_to_world
        self.clicked = []
        self.slept = []
        self.marked_next_day = None

    def find_monthly_card(self):
        return object() if self.card_found else None

    def log_info(self, *args, **kwargs):
        pass

    def tr(self, message):
        return message

    def click_relative(self, x, y, after_sleep=0):
        self.clicked.append((x, y))

    def sleep(self, timeout):
        self.slept.append(timeout)

    def in_team_and_world(self):
        return self.back_to_world

    def wait_until(self, condition, time_out=0, post_action=None, raise_if_not_found=False):
        if self.back_to_world:
            return True
        return None

    def set_check_monthly_card(self, next_day=False):
        self.marked_next_day = next_day


class TestMonthlyCard(unittest.TestCase):

    def test_not_back_to_world_is_not_marked_handled(self):
        # False positive on another screen (e.g. mail/reward UI): two clicks do
        # not return to the world, so the handler must report "not handled" and
        # leave the next-day schedule untouched.
        task = FakeMonthlyCardTask(card_found=True, back_to_world=False)

        handled = BaseWWTask.handle_monthly_card(task)

        self.assertFalse(handled)
        self.assertEqual(task.clicked, [(0.50, 0.89), (0.50, 0.89)])
        self.assertIsNone(task.marked_next_day)

    def test_back_to_world_is_marked_handled(self):
        task = FakeMonthlyCardTask(card_found=True, back_to_world=True)

        handled = BaseWWTask.handle_monthly_card(task)

        self.assertTrue(handled)
        self.assertTrue(task.marked_next_day)

    def test_no_card_does_nothing(self):
        task = FakeMonthlyCardTask(card_found=False, back_to_world=False)

        handled = BaseWWTask.handle_monthly_card(task)

        self.assertFalse(handled)
        self.assertEqual(task.clicked, [])
        self.assertIsNone(task.marked_next_day)


if __name__ == "__main__":
    unittest.main()
