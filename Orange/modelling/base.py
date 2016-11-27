from collections import namedtuple

from Orange.base import Learner, Model

LearnerTypes = namedtuple('LearnerTypes', ['classification', 'regression'])


class FitterMeta(type):
    """Ensure that each subclass of the `Fitter` class overrides the `__fits__`
    attribute with a valid value."""
    def __new__(mcs, name, bases, kwargs):
        # Check that a fitter implementation defines a valid `__fits__`
        if kwargs.get('name', False) and \
                not isinstance(kwargs.get('__fits__'), LearnerTypes):
            raise AssertionError(
                'The `__fits__` property must be an instance of '
                '`Orange.base.LearnerTypes`.')
        return super().__new__(mcs, name, bases, kwargs)


class Fitter(Learner, metaclass=FitterMeta):
    """Handle multiple types of target variable with one learner.

    Subclasses of this class serve as a sort of dispatcher. When subclassing,
    we provide a `LearnerTypes` instance which contain actual learner classes
    that handle appropriate data types. The fitter can then be used on any
    data and will delegate the work to the appropriate learner.

    If the learners that handle each data type require different parameters,
    you should pass in all the possible parameters to the fitter. The fitter
    will then determine which parameters have to be passed to individual
    learners.

    """
    __fits__ = None
    __returns__ = Model

    # Constants to indicate what kind of problem we're dealing with
    CLASSIFICATION, REGRESSION = range(2)

    def __init__(self, preprocessors=None, **kwargs):
        super().__init__(preprocessors=preprocessors)
        self.kwargs = kwargs
        # Make sure to pass preprocessor params to individual learners
        self.kwargs['preprocessors'] = preprocessors
        self.problem_type = None
        self.__learners = {self.CLASSIFICATION: None, self.REGRESSION: None}

    def __call__(self, data):
        # Set the appropriate problem type from the data
        self.problem_type = self.CLASSIFICATION if \
            data.domain.has_discrete_class else self.REGRESSION
        return self.get_learner(self.problem_type)(data)

    def get_learner(self, problem_type):
        """Get the learner for a given problem type."""
        # Prevent trying to access the learner when there's no actual learner
        if problem_type not in self.__handled_problem_types():
            raise AttributeError(
                'There is no learner defined that handles that type of data')
        if self.__learners[problem_type] is None:
            learner = self.__fits__[problem_type](**self.__get_kwargs(
                self.kwargs, problem_type))
            learner.use_default_preprocessors = self.use_default_preprocessors
            self.__learners[problem_type] = learner
        return self.__learners[problem_type]

    def __get_kwargs(self, kwargs, problem_type):
        params = self._get_learner_kwargs(self.__fits__[problem_type])
        return {k: kwargs[k] for k in params & set(kwargs.keys())}

    def __handled_problem_types(self):
        """Get a set of problem types for which we have learners that can
        handle them"""
        types = set()
        if self.__fits__.classification is not None:
            types.add(self.CLASSIFICATION)
        if self.__fits__.regression is not None:
            types.add(self.REGRESSION)
        return types

    @staticmethod
    def _get_learner_kwargs(learner):
        """Get a `set` of kwarg names that belong to the given learner."""
        # Get function params except `self`
        return set(learner.__init__.__code__.co_varnames[1:])

    def __getattr__(self, item):
        return getattr(self.get_learner(self.problem_type), item)
