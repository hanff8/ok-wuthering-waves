import ast
import unittest
from pathlib import Path

from src.task.DomainTask import DomainTask


class TestDomainRecoveryLoop(unittest.TestCase):
    def setUp(self):
        module = ast.parse(Path("src/task/DomainTask.py").read_text(encoding="utf-8"))
        class_node = next(
            node for node in module.body
            if isinstance(node, ast.ClassDef) and node.name == "DomainTask"
        )
        self.method_node = next(
            node for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "farm_domain_with_recovery_loop"
        )

    def test_method_has_retry_parameter_with_default(self):
        args = self.method_node.args.args
        self.assertEqual(args[-1].arg, "max_recovery_retries")
        self.assertEqual(len(self.method_node.args.defaults), 1)
        default_value = self.method_node.args.defaults[0]
        self.assertIsInstance(default_value, ast.Constant)
        self.assertEqual(default_value.value, 3)

    def test_method_increments_retries(self):
        has_increment = any(
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "recovery_retries"
            and isinstance(node.op, ast.Add)
            and isinstance(node.value, ast.Constant)
            and node.value.value == 1
            for node in ast.walk(self.method_node)
        )
        self.assertTrue(has_increment)

    def test_method_stops_when_retry_budget_exceeded(self):
        has_retry_guard = any(
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == "recovery_retries"
            and any(isinstance(op, ast.GtE) for op in node.ops)
            and any(
                isinstance(comp, ast.Name) and comp.id == "max_recovery_retries"
                for comp in node.comparators
            )
            for node in ast.walk(self.method_node)
        )
        self.assertTrue(has_retry_guard)

        has_make_sure_in_world_call = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.func.attr == "make_sure_in_world"
            for node in ast.walk(self.method_node)
        )
        self.assertTrue(has_make_sure_in_world_call)

    def test_loop_unpacks_must_use_from_farm_in_domain(self):
        has_unpack = any(
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Tuple)
            and len(node.targets[0].elts) == 2
            and {elt.id for elt in node.targets[0].elts if isinstance(elt, ast.Name)} == {"finished", "must_use"}
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "farm_in_domain"
            for node in ast.walk(self.method_node)
        )
        self.assertTrue(has_unpack)


class TestDomainStaminaShortfall(unittest.TestCase):
    """日常活跃度没满、体力又凑不满 180 时, 仍要用现有体力刷本。"""

    def make_task(self, stamina):
        task = DomainTask.__new__(DomainTask)
        task.stamina_once = 40
        task.open_F2_book_and_get_stamina = lambda: stamina
        task.sleep = lambda *args, **kwargs: None
        task.backs = []
        task.logs = []
        task.teleports = []
        task.farm_calls = []
        task.back = lambda *args, **kwargs: task.backs.append(kwargs)
        task.log_info = lambda message, **kwargs: task.logs.append(message)
        task.teleport_into_domain_once = lambda: task.teleports.append(1)
        task.farm_in_domain = lambda must_use=0: (task.farm_calls.append(must_use), (True, must_use))[1]
        return task

    def test_farms_with_available_stamina_when_daily_requirement_is_not_met(self):
        task = self.make_task((99, 63, 162))

        task.farm_domain_with_recovery_loop(180, task.teleport_into_domain_once)

        self.assertEqual([1], task.teleports)
        self.assertEqual([162], task.farm_calls)
        self.assertEqual([], task.backs)
        self.assertTrue(any('farm 162 instead' in message for message in task.logs))

    def test_keeps_daily_requirement_when_stamina_is_enough(self):
        task = self.make_task((240, 63, 303))

        task.farm_domain_with_recovery_loop(180, task.teleport_into_domain_once)

        self.assertEqual([1], task.teleports)
        self.assertEqual([180], task.farm_calls)

    def test_aborts_when_stamina_is_below_one_run(self):
        task = self.make_task((20, 0, 20))

        task.farm_domain_with_recovery_loop(180, task.teleport_into_domain_once)

        self.assertEqual([], task.teleports)
        self.assertEqual([{}], task.backs)
        self.assertIn('not enough stamina', task.logs)


if __name__ == "__main__":
    unittest.main()
