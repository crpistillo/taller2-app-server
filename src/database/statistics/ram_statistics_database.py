from src.database.statistics.statistics_database import ApiCall, StatisticsDatabase
from typing import NoReturn, Generator, List
from datetime import datetime

DEFAULT_BATCH_SIZE = 100

class RamStatisticsDatabase(StatisticsDatabase):
    """
    Api statistics database
    """

    def __init__(self):
        self.api_calls = []

    def register_api_call(self, api_call: ApiCall) -> NoReturn:
        """
        Registers an api call

        :param api_call: the api call to register
        """
        self.api_calls.append(api_call)

    def last_days_api_calls(self, days: int) -> Generator[List[ApiCall], None, None]:
        """
        Gets a generator of the last days api calls

        :param days: the number of days back
        :return: a generator of lists of api calls
        """
        batches = len(self.api_calls)//DEFAULT_BATCH_SIZE
        batches += (1 if batches*DEFAULT_BATCH_SIZE < len(self.api_calls) else 0)
        for i in range(batches):
            yield [api_call
                   for api_call in self.api_calls[i*DEFAULT_BATCH_SIZE:(i+1)*DEFAULT_BATCH_SIZE]
                   if abs((datetime.now() - api_call.timestamp).days) <= days]
