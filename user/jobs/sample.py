from django_extensions.management.jobs import BaseJob, MinutelyJob


class Job(MinutelyJob):
    help = "My sample job."

    def execute(self):
        # executing empty sample job
        print("hello world")
