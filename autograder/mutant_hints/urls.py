from django.urls import path

from . import views


urlpatterns = [
    path('mutation_test_suites/<int:mutation_test_suite_pk>/hint_config/',
         views.MutationTestSuiteHintConfigGetCreateView.as_view(),
         name='mutation-test-suite-hint-config'),

    path('mutation_test_suite_hint_configs/<int:pk>/',
         views.MutationTestSuiteHintConfigDetailView.as_view(),
         name='mutation-test-suite-hint-config-detail'),

    path('mutation_test_suite_results/<int:mutation_test_suite_result_pk>/hints/',
         views.UnlockedMutantHintsView.as_view(),
         name='mutation-test-suite-unlocked-hints'),

    path('mutation_test_suite_results/<int:mutation_test_suite_result_pk>/num_hints_remaining/',
         views.NumMutantHintsAvailableView.as_view(),
         name='num-mutant-hints-remaining'),

    path('groups/<int:group_pk>/all_unlocked_mutant_hints/',
         views.AllUnlockedHintsView.as_view(),
         name='all-unlocked-mutant-hints'),

    path('unlocked_mutant_hints/<int:pk>/',
         views.RateHintView.as_view(),
         name='rate-unlocked-mutant-hint'),

    path('mutation_test_suite_results/<int:mutation_test_suite_result_pk>/mutant_hint_limits/',
         views.HintLimitView.as_view(),
         name='mutant-hint-limits')
]
