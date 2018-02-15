from django.conf.urls import include, url
from django.urls.conf import path
from rest_framework import routers

from . import views

handgrading_rubric_detail_router = routers.SimpleRouter()
handgrading_rubric_detail_router.register(r'handgrading_rubrics',
                                          views.HandgradingRubricDetailViewSet,
                                          base_name='handgrading-rubric')

annotation_detail_router = routers.SimpleRouter()
annotation_detail_router.register(r'annotations',
                                  views.AnnotationDetailViewSet,
                                  base_name='annotation')

criterion_detail_router = routers.SimpleRouter()
criterion_detail_router.register(r'criteria',
                                 views.CriterionDetailViewSet,
                                 base_name='criterion')

applied_annotation_detail_router = routers.SimpleRouter()
applied_annotation_detail_router.register(r'applied_annotations',
                                          views.AppliedAnnotationDetailViewSet,
                                          base_name='applied-annotation')


criterion_result_detail_router = routers.SimpleRouter()
criterion_result_detail_router.register(r'criterion_results',
                                        views.CriterionResultDetailViewSet,
                                        base_name='criterion-result')

comment_detail_router = routers.SimpleRouter()
comment_detail_router.register(r'comments',
                               views.CommentDetailViewSet,
                               base_name='comment')


urlpatterns = [
    url(r'^projects/(?P<project_pk>[0-9]+)/handgrading_rubric/$',
        views.HandgradingRubricRetrieveCreateView.as_view(), name='handgrading_rubric'),
    url(r'', include(handgrading_rubric_detail_router.urls)),

    url(r'^handgrading_rubrics/(?P<handgrading_rubric_pk>[0-9]+)/annotations/$',
        views.AnnotationListCreateView.as_view(), name='annotations'),
    path('handgrading_rubrics/<int:handgrading_rubric_pk>/annotations/order/',
        views.AnnotationOrderView.as_view(), name='annotation_order'),
    url(r'', include(annotation_detail_router.urls)),

    url(r'^handgrading_rubrics/(?P<handgrading_rubric_pk>[0-9]+)/criteria/$',
        views.CriterionListCreateView.as_view(), name='criteria'),
    path('handgrading_rubrics/<int:handgrading_rubric_pk>/criteria/order/',
        views.CriterionOrderView.as_view(), name='criterion_order'),
    url(r'', include(criterion_detail_router.urls)),

    url(r'^submission_groups/(?P<group_pk>[0-9]+)/handgrading_result/$',
        views.HandgradingResultView.as_view(), name='handgrading_result'),

    url(r'^handgrading_results/(?P<handgrading_result_pk>[0-9]+)/applied_annotations/$',
        views.AppliedAnnotationListCreateView.as_view(), name='applied_annotations'),
    url(r'', include(applied_annotation_detail_router.urls)),

    url(r'^handgrading_results/(?P<handgrading_result_pk>[0-9]+)/comments/$',
        views.CommentListCreateView.as_view(), name='comments'),
    url(r'', include(comment_detail_router.urls)),

    url(r'^handgrading_results/(?P<handgrading_result_pk>[0-9]+)/criterion_results/$',
        views.CriterionResultListCreateView.as_view(), name='criterion_results'),
    url(r'', include(criterion_result_detail_router.urls)),

    path('projects/<int:pk>/handgrading_results/', views.ListHandgradingResultsView.as_view(),
         name='handgrading_results')
]
