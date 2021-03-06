import json
import uuid
from datetime import datetime

import pytz
import requests
import warnings

from unittest import skip
from pykechain.enums import Category, ActivityType, ActivityStatus
from pykechain.exceptions import NotFoundError, MultipleFoundError, APIError, IllegalArgumentError
from pykechain.models import Part
from pykechain.models.inspector_base import Customization
from pykechain.models.inspectors import SuperGrid, PropertyGrid
from tests.classes import TestBetamax

ISOFORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TestActivities(TestBetamax):
    def test_retrieve_activities(self):
        self.assertTrue(self.project.activities())

    def test_retrieve_single_activity(self):
        self.assertTrue(self.project.activity('Specify wheel diameter'))

    def test_retrieve_unknown_activity(self):
        with self.assertRaises(NotFoundError):
            self.project.activity('Hello?!')

    def test_retrieve_too_many_activity(self):
        with self.assertRaises(MultipleFoundError):
            self.project.activity()

    def test_retrieve_single_bike(self):
        activity = self.project.activity('Specify wheel diameter')

        parts = activity.parts()

        self.assertEqual(len(parts), 2)

    def test_create_activity(self):
        project = self.project

        subprocess = project.create_activity('Random', activity_class='Subprocess')

        self.assertEqual(subprocess.name, 'Random')

        task = subprocess.create('Another')

        subprocess.delete()

        with self.assertRaises(APIError):
            subprocess.delete()

    def test_create_activity_under_task(self):
        task = self.project.activity('Customized task')

        with self.assertRaises(IllegalArgumentError):
            task.create('This cannot happen')

    def test_configure_activity(self):
        project = self.project

        bike = project.model('Bike')
        wheel = project.model('Wheel')

        task = project.create_activity('Random')

        task.configure([
            bike.property('Gears'),
            bike.property('Total height')
        ], [
            wheel.property('Spokes')
        ])

        task.delete()

    # new in 1.7
    def test_edit_activity_name(self):
        specify_wd = self.project.activity('Specify wheel diameter')
        specify_wd.edit(name='Specify wheel diameter - updated')

        specify_wd_u = self.project.activity('Specify wheel diameter - updated')
        self.assertEqual(specify_wd.id, specify_wd_u.id)
        self.assertEqual(specify_wd.name, specify_wd_u.name)
        self.assertEqual(specify_wd.name, 'Specify wheel diameter - updated')

        # Added to improve coverage. Assert whether TypeError is raised when 'name' is not a string object.
        with self.assertRaises(TypeError):
            specify_wd.edit(name=True)

        specify_wd.edit(name='Specify wheel diameter')

    def test_edit_activity_description(self):
        specify_wd = self.project.activity('Specify wheel diameter')
        specify_wd.edit(description='This task has an even cooler description')

        self.assertEqual(specify_wd._client.last_response.status_code, requests.codes.ok)

        # Added to improve coverage. Assert whether TypeError is raised when 'description' is not a string object.
        with self.assertRaises(TypeError):
            specify_wd.edit(description=42)

        specify_wd.edit(description='This task has a cool description')

    def test_edit_activity_naive_dates(self):
        specify_wd = self.project.activity('Specify wheel diameter')

        old_start, old_due = datetime.strptime(specify_wd._json_data.get('start_date'), ISOFORMAT), \
                             datetime.strptime(specify_wd._json_data.get('due_date'), ISOFORMAT)
        start_time = datetime(2000, 1, 1, 0, 0, 0)
        due_time = datetime(2019, 12, 31, 0, 0, 0)

        with warnings.catch_warnings(record=False) as w:
            warnings.simplefilter("ignore")
            specify_wd.edit(start_date=start_time, due_date=due_time)

        self.assertEqual(specify_wd._client.last_response.status_code, requests.codes.ok)

        # Added to improve coverage. Assert whether TypeError is raised when 'start_date' and 'due_date are not
        # datetime objects
        with self.assertRaises(TypeError):
            specify_wd.edit(start_date='All you need is love')

        with self.assertRaises(TypeError):
            specify_wd.edit(due_date='Love is all you need')

        specify_wd_u = self.project.activity('Specify wheel diameter')

        self.assertEqual(specify_wd.id, specify_wd_u.id)

        specify_wd.edit(start_date=old_start, due_date=old_due)

    def test_edit_due_date_timezone_aware(self):
        specify_wd = self.project.activity('Specify wheel diameter')

        # save old values
        old_start, old_due = datetime.strptime(specify_wd._json_data.get('start_date'), ISOFORMAT), \
                             datetime.strptime(specify_wd._json_data.get('due_date'), ISOFORMAT)

        startdate = datetime.now(pytz.utc)
        duedate = datetime(2019, 1, 1, 0, 0, 0, tzinfo=pytz.timezone('Europe/Amsterdam'))

        specify_wd.edit(start_date=startdate, due_date=duedate)

        self.assertEqual(specify_wd._client.last_response.status_code, requests.codes.ok)

        # teardown
        specify_wd.edit(start_date=old_start, due_date=old_due)

    def test_edit_activity_assignee(self):
        specify_wd = self.project.activity('Specify wheel diameter')
        original_assignee = specify_wd._json_data.get('assignees', ['testuser', 'testmanager'])

        specify_wd.edit(assignees=['pykechain'])

        specify_wd = self.project.activity('Specify wheel diameter')
        self.assertEqual(['pykechain'], specify_wd._json_data.get('assignees'))

        self.assertEqual(specify_wd._client.last_response.status_code, requests.codes.ok)

        # Added to improve coverage. Assert whether NotFoundError is raised when 'assignee' is not part of the
        # scope members
        with self.assertRaises(NotFoundError):
            specify_wd.edit(assignees=['Not Member'])

        # Added to improve coverage. Assert whether NotFoundError is raised when 'assignee' is not part of the
        # scope members
        with self.assertRaises(TypeError):
            specify_wd.edit(assignees='Not Member')

        specify_wd.edit(assignees=original_assignee)

    # 1.10.0
    def test_edit_activity_status(self):
        specify_wd = self.project.activity('Specify wheel diameter')
        original_status = specify_wd.status

        specify_wd.edit(status=ActivityStatus.COMPLETED)

        # Added to improve coverage. Assert whether TypeError is raised when 'status' is not a string
        with self.assertRaises(TypeError):
            specify_wd.edit(status=True)

        # If the status is not part of Enums.Status then it should raise an APIError
        with self.assertRaises(APIError):
            specify_wd.edit(status='NO STATUS')

        # Return the status to how it used to be
        specify_wd.edit(status=original_status)

    # 1.7.2
    def test_datetime_with_naive_duedate_only_fails(self):
        """reference to #121 - thanks to @joost.schut"""
        # setup
        specify_wd = self.project.activity('Specify wheel diameter')

        # save old values
        old_start, old_due = datetime.strptime(specify_wd._json_data.get('start_date'), ISOFORMAT), \
                             datetime.strptime(specify_wd._json_data.get('due_date'), ISOFORMAT)
        naive_duedate = datetime(2017, 6, 5, 5, 0, 0)
        with warnings.catch_warnings(record=False) as w:
            warnings.simplefilter("ignore")
            specify_wd.edit(due_date=naive_duedate)

        # teardown
        with warnings.catch_warnings(record=False) as w:
            warnings.simplefilter("ignore")
            specify_wd.edit(due_date=old_due)

    def test_datetime_with_tzinfo_provides_correct_offset(self):
        """reference to #121 - thanks to @joost.schut

        The tzinfo.timezone('Europe/Amsterdam') should provide a 2 hour offset, recording 20 minutes
        """
        # setup
        specify_wd = self.project.activity('Specify wheel diameter')
        # save old values
        old_start, old_due = datetime.strptime(specify_wd._json_data.get('start_date'), ISOFORMAT), \
                             datetime.strptime(specify_wd._json_data.get('due_date'), ISOFORMAT)

        tz = pytz.timezone('Europe/Amsterdam')
        tzaware_due = tz.localize(datetime(2017, 7, 1))
        tzaware_start = tz.localize(datetime(2017, 6, 30, 0, 0, 0))

        specify_wd.edit(start_date=tzaware_start)
        self.assertTrue(specify_wd._json_data['start_date'], tzaware_start.isoformat(sep='T'))
        self.assertRegexpMatches(specify_wd._json_data['start_date'], r'^.*(\+02:00|\+01:00)$')

        specify_wd.edit(due_date=tzaware_due)
        self.assertTrue(specify_wd._json_data['due_date'], tzaware_due.isoformat(sep='T'))
        self.assertRegexpMatches(specify_wd._json_data['due_date'], r'^.*(\+02:00|\+01:00)$')

        # teardown
        with warnings.catch_warnings(record=False) as w:
            warnings.simplefilter("ignore")
            specify_wd.edit(start_date=old_start, due_date=old_due)

    # 1.8
    def test_retrieve_subprocess_of_task(self):
        task = self.project.activity(name='SubTask')
        subprocess = task.subprocess()  # type Activity
        self.assertEqual(subprocess.activity_type, ActivityType.SUBPROCESS)

    def test_retrieve_subprocess_of_a_toplevel_task(self):
        task = self.project.activity('Specify wheel diameter')
        with self.assertRaises(NotFoundError):
            subprocess = task.subprocess()

    def test_retrieve_children_of_subprocess(self):
        subprocess = self.project.activity(name='Subprocess')  # type: Activity
        children = subprocess.children()
        self.assertTrue(len(children) >= 1)
        for child in children:
            self.assertEqual(child._json_data.get('container'), subprocess.id)

    def test_retrieve_children_of_task(self):
        task = self.project.activity(name='SubTask')
        with self.assertRaises(NotFoundError):
            task.children()

    def test_retrieve_activity_by_id(self):
        task = self.project.activity(name='SubTask')  # type: Activity

        task_by_id = self.client.activity(pk=task.id)

        self.assertEqual(task.id, task_by_id.id)

    def test_retrieve_siblings_of_a_task_in_a_subprocess(self):
        task = self.project.activity(name='SubTask')  # type: Activity
        siblings = task.siblings()

        self.assertTrue(task.id in [sibling.id for sibling in siblings])
        self.assertTrue(len(siblings) >= 1)

    def test_retrieve_part_associated_to_activities(self):
        task = self.project.activity('Specify wheel diameter')
        parts = list(task.parts())

        for part in parts:
            self.assertIsInstance(part, Part)
            self.assertTrue(part.category == Category.INSTANCE)

    def test_retrieve_part_models_associated_to_activities(self):
        task = self.project.activity('Specify wheel diameter')
        models = list(task.parts(category=Category.MODEL))

        for model in models:
            self.assertIsInstance(model, Part)
            self.assertTrue(model.category == Category.MODEL)
            if model.name == 'Bike':
                self.assertTrue(not model.property('Gears').output)
            elif model.name == 'Front Fork':
                self.assertTrue(model.property('Material').output)

    def test_retrieve_associated_parts_to_activity(self):
        task = self.project.activity('Specify wheel diameter')
        (models, parts) = list(task.associated_parts())

        for part in models:
            self.assertIsInstance(part, Part)
            self.assertTrue(part.category == Category.MODEL)

        for part in parts:
            self.assertIsInstance(part, Part)
            self.assertTrue(part.category == Category.INSTANCE)

    # updated and new in 1.9
    @skip('KE-chain deprecated the inspector components')
    def test_customize_activity_with_widget_config(self):
        # Retrieve the activity to be customized
        activity_to_costumize = self.project.activity('Customized task')

        # Create the widget config it should have now
        widget_config = {'components': [{'xtype': 'superGrid', 'filter':
            {'parent': 'e5106946-40f7-4b49-ae5e-421450857911',
             'model': 'edc8eba0-47c5-415d-8727-6d927543ee3b'}}]}

        # Customize it with a config
        activity_to_costumize.customize(
            config=widget_config)

        # Re-retrieve it
        activity_to_costumize = self.project.activity('Customized task')

        # Check whether it's widget config has changed
        self.assertTrue(activity_to_costumize._json_data['widget_config']['config'] != '{}')

        # Change it back to an empty config
        activity_to_costumize.customize(config={})

    @skip('KE-chain deprecated the inspector components')
    def test_customize_new_activity(self):
        # Create the activity to be freshly customized
        new_task = self.project.create_activity('New task')

        # Customize it with a config
        new_task.customize(
            config={"components": [{
                "xtype": "superGrid",
                "filter": {
                    "parent": "e5106946-40f7-4b49-ae5e-421450857911",
                    "model": "edc8eba0-47c5-415d-8727-6d927543ee3b"}}]})

        # Retrieve it again
        new_task = self.project.activity('New task')

        # Check whether it's widget config has changed
        self.assertTrue(new_task._json_data['widget_config']['config'] is not None)

        # Delete it
        new_task.delete()

    @skip('KE-chain deprecated the inspector components')
    def test_customize_activity_with_inspectorcomponent(self):
        # Create the activity to be freshly customized
        new_task = self.project.create_activity('New task (test_customize_activity_with_insp_component)')

        customization = Customization()
        supergrid = SuperGrid(parent=str(uuid.uuid4()), model=str(uuid.uuid4()))
        customization.add_component(supergrid)

        # set as new customization in the task
        new_task.customize(customization)

        # retrieve and make another oene
        new_task2 = self.project.activity(new_task.name)

        propertygrid = PropertyGrid(part=str(uuid.uuid4()), title="new name")
        customization = Customization()
        customization.add_component(propertygrid)
        new_task2.customize(customization)

        self.assertTrue(new_task._json_data['widget_config']['config'] is not None)
        self.assertTrue(new_task2._json_data['widget_config']['config'] is not None)

        # the customization from the activity still validates
        Customization(json.loads(new_task2._json_data['widget_config']['config'])).validate()

        # teardown
        new_task.delete()

    def test_wrong_customization(self):
        # Set up
        new_task = self.project.create_activity('Task for wrong customization')
        config = 'This will not work'

        with self.assertRaises(Exception):
            new_task.customize(config)

        # teardown
        new_task.delete()
