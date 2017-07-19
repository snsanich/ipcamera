import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Any, Callable, List  # NOQA
import logging
import threading
from async import (
    run_coroutine_threadsafe, run_callback_threadsafe,
    fire_coroutine_threadsafe)
from async_timeout import timeout
import enum

_LOGGER = logging.getLogger(__name__)

# How long to wait till things that run on startup have to finish.
TIMEOUT_EVENT_START = 15

def callback(func: Callable[..., None]) -> Callable[..., None]:
    """Annotation to mark method as safe to call from within the event loop."""
    # pylint: disable=protected-access
    func._hass_callback = True
    return func

@callback
def async_loop_exception_handler(loop, context):
    """Handle all exception inside the core loop."""
    kwargs = {}
    exception = context.get('exception')
    if exception:
        kwargs['exc_info'] = (type(exception), exception,
                              exception.__traceback__)

    _LOGGER.error("Error doing job: %s", context['message'], **kwargs)

def is_callback(func: Callable[..., Any]) -> bool:
    """Check if function is safe to be called in the event loop."""
    return '_hass_callback' in func.__dict__

class CoreState(enum.Enum):
    """Represent the current state of Home Assistant."""

    not_running = 'NOT_RUNNING'
    starting = 'STARTING'
    running = 'RUNNING'
    stopping = 'STOPPING'

    def __str__(self) -> str:
        """Return the event."""
        return self.value



class HomeAssistant(object):
    """Root object of the Home Assistant home automation."""

    def __init__(self, loop=None):
        """Initialize new Home Assistant object."""
        if sys.platform == 'win32':
            self.loop = loop or asyncio.ProactorEventLoop()
        else:
            self.loop = loop or asyncio.get_event_loop()

        executor_opts = {'max_workers': 10}
        if sys.version_info[:2] >= (3, 5):
            # It will default set to the number of processors on the machine,
            # multiplied by 5. That is better for overlap I/O workers.
            executor_opts['max_workers'] = None
        if sys.version_info[:2] >= (3, 6):
            executor_opts['thread_name_prefix'] = 'SyncWorker'

        self.executor = ThreadPoolExecutor(**executor_opts)
        self.loop.set_default_executor(self.executor)
        self.loop.set_exception_handler(async_loop_exception_handler)
        self._pending_tasks = []
        self._track_task = True
        # This is a dictionary that any component can store any data on.
        self.data = {}
        self.state = CoreState.not_running
        self.exit_code = None

    @property
    def is_running(self) -> bool:
        """Return if Home Assistant is running."""
        return self.state in (CoreState.starting, CoreState.running)

    def start(self) -> None:
        """Start home assistant."""
        # Register the async start
        fire_coroutine_threadsafe(self.async_start(), self.loop)

        # Run forever and catch keyboard interrupt
        try:
            # Block until stopped
            _LOGGER.info("Starting Home Assistant core loop")
            self.loop.run_forever()
            return self.exit_code
        except KeyboardInterrupt:
            self.loop.call_soon_threadsafe(
                self.loop.create_task, self.async_stop())
            self.loop.run_forever()
        finally:
            self.loop.close()

    @asyncio.coroutine
    def async_start(self):
        """Finalize startup from inside the event loop.

        This method is a coroutine.
        """
        _LOGGER.info("Starting Home Assistant")
        self.state = CoreState.starting

        # pylint: disable=protected-access
        self.loop._thread_ident = threading.get_ident()

        try:
            # Only block for EVENT_HOMEASSISTANT_START listener
            self.async_stop_track_tasks()
            with timeout(TIMEOUT_EVENT_START, loop=self.loop):
                yield from self.async_block_till_done()
        except asyncio.TimeoutError:
            _LOGGER.warning(
                'Something is blocking Home Assistant from wrapping up the '
                'start up phase. We\'re going to continue anyway. Please '
                'report the following info at http://bit.ly/2ogP58T : %s',
                ', '.join(self))

        # Allow automations to set up the start triggers before changing state
        yield from asyncio.sleep(0, loop=self.loop)
        self.state = CoreState.running

    def add_job(self, target: Callable[..., None], *args: Any) -> None:
        """Add job to the executor pool.

        target: target to call.
        args: parameters for method to call.
        """
        if target is None:
            raise ValueError("Don't call add_job with None")
        self.loop.call_soon_threadsafe(self.async_add_job, target, *args)

    @callback
    def async_add_job(self, target: Callable[..., None], *args: Any) -> None:
        """Add a job from within the eventloop.

        This method must be run in the event loop.

        target: target to call.
        args: parameters for method to call.
        """
        task = None

        if asyncio.iscoroutine(target):
            task = self.loop.create_task(target)
        elif is_callback(target):
            self.loop.call_soon(target, *args)
        elif asyncio.iscoroutinefunction(target):
            task = self.loop.create_task(target(*args))
        else:
            task = self.loop.run_in_executor(None, target, *args)

        # If a task is sheduled
        if self._track_task and task is not None:
            self._pending_tasks.append(task)

        return task

    @callback
    def async_track_tasks(self):
        """Track tasks so you can wait for all tasks to be done."""
        self._track_task = True

    @callback
    def async_stop_track_tasks(self):
        """Stop track tasks so you can't wait for all tasks to be done."""
        self._track_task = False

    @callback
    def async_run_job(self, target: Callable[..., None], *args: Any) -> None:
        """Run a job from within the event loop.

        This method must be run in the event loop.

        target: target to call.
        args: parameters for method to call.
        """
        if not asyncio.iscoroutine(target) and is_callback(target):
            target(*args)
        else:
            self.async_add_job(target, *args)

    def block_till_done(self) -> None:
        """Block till all pending work is done."""
        run_coroutine_threadsafe(
            self.async_block_till_done(), loop=self.loop).result()

    @asyncio.coroutine
    def async_block_till_done(self):
        """Block till all pending work is done."""
        # To flush out any call_soon_threadsafe
        yield from asyncio.sleep(0, loop=self.loop)

        while self._pending_tasks:
            pending = [task for task in self._pending_tasks
                       if not task.done()]
            self._pending_tasks.clear()
            if pending:
                yield from asyncio.wait(pending, loop=self.loop)
            else:
                yield from asyncio.sleep(0, loop=self.loop)

    def stop(self) -> None:
        """Stop Home Assistant and shuts down all threads."""
        fire_coroutine_threadsafe(self.async_stop(), self.loop)

    @asyncio.coroutine
    def async_stop(self, exit_code=0) -> None:
        """Stop Home Assistant and shuts down all threads.

        This method is a coroutine.
        """
        # stage 1
        self.state = CoreState.stopping
        self.async_track_tasks()
        yield from self.async_block_till_done()

        # stage 2
        self.state = CoreState.not_running
        yield from self.async_block_till_done()
        self.executor.shutdown()

        self.exit_code = exit_code
        self.loop.stop()
