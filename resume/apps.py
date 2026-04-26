from django.apps import AppConfig


class ResumeConfig(AppConfig):
    name = 'resume'
    _model_bootstrapped = False

    def ready(self):
        if ResumeConfig._model_bootstrapped:
            return
        ResumeConfig._model_bootstrapped = True

        from .ml.predictor import ensure_model_artifacts

        ensure_model_artifacts()
