from django.conf.urls import include, url
from django.urls.conf import path
from rest_framework import routers

from . import views

comment_detail_router = routers.SimpleRouter()
comment_detail_router.register(r'comments',
                               views.CommentDetailViewSet,
                               basename='comment')


urlpatterns = [
    path('projects/<int:project_pk>/handgrading_rubric/',
         views.GetCreateHandgradingRubricView.as_view(),
         name='handgrading_rubric'),
    path('handgrading_rubrics/<int:pk>/',
         views.HandgradingRubricDetailView.as_view(),
         name='handgrading-rubric-detail'),

    path('handgrading_rubrics/<int:handgrading_rubric_pk>/annotations/',
         views.ListCreateAnnotationView.as_view(), name='annotations'),
    path('annotations/<int:pk>/', views.AnnotationDetailView.as_view(), name='annotation-detail'),
    path('handgrading_rubrics/<int:handgrading_rubric_pk>/annotations/order/',
         views.AnnotationOrderView.as_view(), name='annotation_order'),

    path('handgrading_rubrics/<int:handgrading_rubric_pk>/criteria/',
         views.ListCreateCriterionView.as_view(), name='criteria'),
    path('criteria/<int:pk>/', views.CriterionDetailView.as_view(), name='criterion-detail'),
    path('handgrading_rubrics/<int:handgrading_rubric_pk>/criteria/order/',
         views.CriterionOrderView.as_view(), name='criterion_order'),

    path('groups/<int:group_pk>/handgrading_result/',
         views.HandgradingResultView.as_view(),
         name='handgrading_result'),
    path('groups/<int:group_pk>/handgrading_result/file/',
         views.HandgradingResultFileContentView.as_view(),
         name='handgrading-result-file'),
    path('groups/<int:group_pk>/handgrading_result/has_correct_submission/',
         views.HandgradingResultHasCorrectSubmissionView.as_view(),
         name='handgrading-result-has-correct-submission'),

    path('handgrading_results/<int:handgrading_result_pk>/applied_annotations/',
         views.ListCreateAppliedAnnotationView.as_view(), name='applied_annotations'),
    path('applied_annotations/<int:pk>/', views.AppliedAnnotationDetailView.as_view(),
         name='applied-annotation-detail'),

    url(r'^handgrading_results/(?P<handgrading_result_pk>[0-9]+)/comments/$',
        views.CommentListCreateView.as_view(), name='comments'),
    url(r'', include(comment_detail_router.urls)),

    path('handgrading_results/<int:handgrading_result_pk>/criterion_results/',
         views.ListCreateCriterionResultView.as_view(), name='criterion_results'),
    path('criterion_results/<int:pk>/', views.CriterionResultDetailView.as_view(),
         name='criterion-result-detail'),

    path('projects/<int:pk>/handgrading_results/', views.ListHandgradingResultsView.as_view(),
         name='handgrading_results')
]
