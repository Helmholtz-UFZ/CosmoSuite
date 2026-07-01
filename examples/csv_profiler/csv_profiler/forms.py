"""CSV profiler input form (FormFactory bound to ProfileConfig).

Lives in the domain because the form is domain-specific; the framework layouts
provide only generic UI helpers.
"""

import dash_bootstrap_components as dbc
from dash_form_factory import FormFactory, InputField

from csv_profiler.pydantic_models import ProfileConfig

form_layout_template = dbc.Card(
    [
        dbc.CardHeader("Profiling Options", className="text-center fs-5"),
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(InputField("handle_missing"), md=6),
                        dbc.Col(InputField("histogram_bins"), md=6),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(InputField("top_n_categories"), md=6),
                        dbc.Col(InputField("compute_correlation"), md=6),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(InputField("trigger_error"), md=6),
                    ],
                    className="mb-3",
                ),
            ],
        ),
    ],
    className="my-3",
)

form_factory = FormFactory(ProfileConfig, form_layout_template)
form_layout = form_factory.process_layout(form_factory.layout)
