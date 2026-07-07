"""数据模型与关系测试。"""

from app.models.pipeline import TASK_STATUSES, TASK_TYPES, RenderTask
from app.models.production import Keyframe, Shot
from app.models.project import Character, Project


def test_create_project_with_shot(db_session):
    """项目与镜头的关系应正确建立。"""
    proj = Project(title="模型测试", status="planning")
    db_session.add(proj)
    db_session.commit()

    shot = Shot(project_id=proj.id, shot_code="S01_01", scene="废墟苏醒", duration=5.0)
    db_session.add(shot)
    db_session.commit()

    assert shot.id is not None
    assert shot.project.title == "模型测试"
    assert shot.gen_method == "wan_i2v"


def test_keyframe_relationship(db_session):
    """镜头与关键帧的一对多关系。"""
    proj = Project(title="关键帧测试")
    db_session.add(proj)
    db_session.commit()

    shot = Shot(project_id=proj.id, shot_code="S01_02")
    db_session.add(shot)
    db_session.commit()

    kf = Keyframe(shot_id=shot.id, label="S01_02", prompt="Ava walking", seed=1001)
    db_session.add(kf)
    db_session.commit()

    assert len(shot.keyframes) == 1
    assert shot.keyframes[0].label == "S01_02"
    assert shot.keyframes[0].seed == 1001


def test_character_anchor_prompt(db_session):
    """角色锚点提示词可正确存取。"""
    proj = Project(title="角色测试")
    db_session.add(proj)
    db_session.commit()

    char = Character(
        project_id=proj.id,
        name="艾娃",
        anchor_prompt="Ava, 28-year-old woman, short dark hair...",
        reference_images=["01_Assets/Characters/Ava/front.png"],
    )
    db_session.add(char)
    db_session.commit()

    assert char.id is not None
    assert char.reference_images[0].endswith("front.png")


def test_render_task_constants():
    """任务类型与状态常量完整。"""
    assert "keyframe" in TASK_TYPES
    assert "video_i2v" in TASK_TYPES
    assert "kling" in TASK_TYPES
    assert "tts" in TASK_TYPES
    assert "music" in TASK_TYPES
    assert "pending" in TASK_STATUSES
    assert "completed" in TASK_STATUSES


def test_render_task_default_retry(db_session):
    """渲染任务默认重试次数与状态。"""
    proj = Project(title="队列测试")
    db_session.add(proj)
    db_session.commit()

    task = RenderTask(project_id=proj.id, task_type="keyframe", prompt="生成关键帧")
    db_session.add(task)
    db_session.commit()

    assert task.max_retry == 3
    assert task.retry_count == 0
    assert task.status == "pending"
    assert task.priority == 0
