from lxml import etree
from dataclasses import dataclass
from funcy import first, all


@dataclass
class Job:
    job_id: str
    status: str
    result: str
    whiteboard: str
    hostname: str

    @property
    def is_reserved(self):
        return self.status == "Reserved" and self.result == "Pass"

    @property
    def is_running(self):
        return self.status == "Running" and self.result == "Pass"


@dataclass(frozen=True)
class Task:
    name: str
    status: str
    result: str

    @property
    def is_completed(self):
        return self.status == "Completed" and self.result in ("Pass", "New")


@dataclass(frozen=True)
class Report:
    job: Job
    tasks: list[Task]

    @classmethod
    def from_beaker_results(cls, xml: str):
        root = etree.XML(xml)
        element = first(root.xpath("/job"))
        whiteboard = first(root.xpath("/job/whiteboard")).text
        hostname = first(root.xpath("/job/recipeSet/recipe/@system"))
        report = cls(
            Job(
                element.attrib["id"],
                element.attrib["status"],
                element.attrib["result"],
                whiteboard,
                hostname,
            ),
            list(
                Task(el.attrib["name"], el.attrib["status"], el.attrib["result"])
                for el in root.xpath("/job/recipeSet/recipe/task")
            ),
        )
        return report

    @property
    def is_reserved(self):
        return self.job.is_reserved and all(task.is_completed for task in self.tasks)

    @property
    def is_completed_except_reservesysTask(self):
        runningReservesysTask = Task(
            name="/distribution/reservesys", status="Running", result="New"
        )
        return self.job.is_running and all(
            task.is_completed
            for task in (set(self.tasks) - set((runningReservesysTask,)))
        )
