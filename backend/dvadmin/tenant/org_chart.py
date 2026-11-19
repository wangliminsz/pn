# -*- coding: utf-8 -*-
"""
租户组织架构服务
- 模板批量导入: 部门 → 用户 + 职级(经理/主管/员工)
- 解析 CSV/XLSX, 支持 dry_run 预览
- 构建组织树(部门 + 成员), 供前端树形编辑器
"""
import csv
import hashlib
import io
import re

from django.db import transaction
from django.utils.translation import gettext as _

# 模板列(顺序固定)
TEMPLATE_HEADERS = ["部门", "上级部门", "姓名", "账号", "手机", "职级"]

# 职级 <-> 角色 key/名称
TIER_ROLE_KEY = {
    "manager": "tenant_manager",
    "supervisor": "tenant_supervisor",
    "staff": "tenant_emp",
}
TIER_LABEL = {
    "manager": "经理",
    "supervisor": "主管",
    "staff": "员工",
}
# 兼容中文/英文输入
TIER_ALIAS = {
    "经理": "manager", "主管": "supervisor", "员工": "staff", "职员": "staff",
    "manager": "manager", "supervisor": "supervisor", "staff": "staff",
}

ROOT_DEPT_MARKERS = {"", "公司", "公司总部", "(公司)", "总部", "-", "company", "(company)",
                     "hq", "headquarters", "(hq)", "root", "top"}

# 表示"公司本身"(挂在公司根节点, 无部门)的部门值; 同时支持填公司名
COMPANY_MARKERS = {"公司", "(公司)", "公司总部", "总部", "-", "company", "(company)",
                   "root", "top", "self", "biz"}


def _is_company_dept(dept, tenant):
    """判断该行是否挂在"公司根"下(不带部门): 部门值等于公司名 或 命中公司标记"""
    if not dept:
        return False
    d = str(dept).strip()
    return d.lower() in COMPANY_MARKERS or d == tenant.name


def _normalize_tier(value):
    """把职级输入归一化为 manager/supervisor/staff, 未知返回 None(兼容中英文/常见拼写)"""
    if not value:
        return None
    v = str(value).strip().lower()
    for alias, tier in TIER_ALIAS.items():
        if v == alias.lower():
            return tier
    return None


def _normalize_row(raw):
    """把一行(dict)归一化为标准字段, 支持中/英文列名(大小写不敏感、忽略下划线/空格/括号)"""
    norm = {}
    for k, v in raw.items():
        if k is None:
            continue
        key = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]", "", str(k).strip().lower())
        if key:
            norm[key] = v

    def get(*names):
        for n in names:
            v = norm.get(n.lower())
            if v is not None and str(v).strip() != "":
                return str(v).strip()
        return ""

    row = {
        "dept": get("部门", "dept", "department", "departmentname", "团队"),
        "parent": get("上级部门", "parent", "parentdept", "upperdept", "parentdepartment"),
        "name": get("姓名", "name", "staffname", "fullname", "employeename"),
        "username": get("账号", "username", "account", "user", "accountname", "login", "员工账号"),
        "mobile": get("手机", "mobile", "phone", "tel", "mobileno", "phonenumber"),
        "tier_raw": get("职级", "tier", "role", "grade", "level", "岗位级"),
    }
    row["tier"] = _normalize_tier(row["tier_raw"])
    # "纯部门"行: 只声明部门/上级, 无人员信息 → 仅用于构建组织架构, 不建账号
    row["is_dept_only"] = bool(row["dept"]) and not (row["name"] or row["username"] or row["tier_raw"])
    errors = []
    if not row["dept"]:
        errors.append(_("Dept is required"))
    elif not row["is_dept_only"]:
        if not row["name"]:
            errors.append(_("Name is required"))
        if not row["username"]:
            errors.append(_("Account is required"))
        if not row["tier"]:
            errors.append(_("Unrecognized tier: {}").format(row["tier_raw"]))
        # 账号: 允许字母/数字/下划线/中划线/点 以及 邮箱(@, 含 +)
        if row["username"] and not re.fullmatch(r"[A-Za-z0-9@\._\-+]+", row["username"]):
            errors.append(_("Account contains invalid characters (only letters/numbers/underscore/hyphen/dot/@ allowed)"))
    row["errors"] = errors
    return row


def parse_inline_rows(rows):
    """从 JSON 传入的 rows(list[dict]) 解析为标准化行"""
    return [_normalize_row(r) for r in rows]


def parse_file(file_obj):
    """解析上传文件(CSV/XLSX)为标准化行"""
    filename = (getattr(file_obj, "name", "") or "").lower()
    raw_rows = []
    data = file_obj.read()
    if filename.endswith((".xls", ".xlsx")):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        ws = wb.active
        rows = ws.iter_rows(values_only=True)
        header = None
        for idx, values in enumerate(rows):
            if values is None or all(v is None or str(v).strip() == "" for v in values):
                continue
            if idx == 0:
                header = [str(v).strip() if v is not None else "" for v in values]
                continue
            raw_rows.append(dict(zip(header, values)))
    else:
        text = data.decode("utf-8-sig", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        header = None
        for idx, values in enumerate(reader):
            if not values or all(str(v).strip() == "" for v in values):
                continue
            if idx == 0:
                header = [str(v).strip() for v in values]
                continue
            raw_rows.append(dict(zip(header, values)))
    return [_normalize_row(r) for r in raw_rows]


def _get_roles(tenant):
    """确保该租户具备三个职级角色, 返回 {tier: role}"""
    from dvadmin.system.models import Role

    result = {}
    for tier, role_key in TIER_ROLE_KEY.items():
        role = Role.objects.filter(tenant=tenant, key=role_key).first()
        if not role:
            role = Role.objects.create(
                tenant=tenant,
                key=role_key,
                name=TIER_LABEL[tier],
                sort={"manager": 1, "supervisor": 2, "staff": 3}[tier],
                status=True,
            )
        result[tier] = role
    return result


# 租户标准业务菜单集(按 web_path 定位, 与「租户9」手动授权一致; 新租户自动授权同一套)
MENU_BASE_PATHS = ["/home", "/system", "/property", "/linebot", "/groupdoc", "/calendar", "/personal", "/changelog", "/payment"]
MENU_MANAGER_ONLY_PATHS = ["/broadcast", "/org"]


def ensure_tenant_tier_roles(tenant):
    """确保租户三角色(经理/主管/员工)存在, 并授予全部业务按钮权限 + 按档位写 data_range + 菜单授权
    经理=3(本租户全部)/主管=1(本部门及以下)/员工=0(仅本人)。幂等, 可重复调用。
    导入 org-chart 后自动调用, 避免新租户角色无权限/数据范围错误/页面404。
    """
    from dvadmin.system.models import Menu, MenuButton, RoleMenuButtonPermission, RoleMenuPermission

    result = _get_roles(tenant)
    all_buttons = MenuButton.objects.all()
    # 菜单授权: 核心逻辑 init_tenant_menus 命令与这里是同一套
    menus_by_path = {}
    for m in Menu.objects.all():
        if m.web_path:
            menus_by_path[m.web_path] = m
    for tier, role in result.items():
        scope = {"manager": 3, "supervisor": 1, "staff": 0}[tier]
        for btn in all_buttons:
            RoleMenuButtonPermission.objects.update_or_create(
                role=role, menu_button=btn, defaults={"data_range": scope},
            )
        paths = list(MENU_BASE_PATHS)
        if tier == "manager":
            paths += MENU_MANAGER_ONLY_PATHS
        for p in paths:
            menu = menus_by_path.get(p)
            if menu and not RoleMenuPermission.objects.filter(role=role, menu=menu).exists():
                RoleMenuPermission.objects.create(role=role, menu=menu)
    return result


def _dept_key(tenant, dept_name):
    """生成全局唯一的部门 key"""
    from dvadmin.system.models import Dept

    base = f"{tenant.tenant_code}_{dept_name}"
    key = re.sub(r"[^A-Za-z0-9_]", "_", base)[:60]
    if not Dept.objects.filter(key=key).exists():
        return key
    i = 2
    while Dept.objects.filter(key=f"{key}_{i}").exists():
        i += 1
    return f"{key}_{i}"


def _ensure_dept(tenant, dept_name, parent_name, memo, created_log):
    """
    确保部门存在(递归创建父级), 返回 (dept, created)
    memo: {name: dept} 本次导入的缓存, 用于同批次去重/循环引用
    """
    from dvadmin.system.models import Dept

    if dept_name in memo:
        return memo[dept_name], False
    parent_name = (parent_name or "").strip()
    is_root = parent_name in ROOT_DEPT_MARKERS or parent_name == tenant.name
    parent = None
    if not is_root and parent_name:
        parent, _ = _ensure_dept(tenant, parent_name, "", memo, created_log)

    # 数据库中已有同名部门(该租户下)
    dept = Dept.objects.filter(tenant=tenant, name=dept_name, parent=parent).first()
    created = False
    if not dept:
        dept = Dept.objects.create(
            tenant=tenant,
            name=dept_name,
            key=_dept_key(tenant, dept_name),
            parent=parent,
            sort=len(created_log) + 1,
            status=True,
        )
        created = True
    memo[dept_name] = dept
    if created:
        created_log.append(dept_name)
    return dept, created


def _group_duplicates(rows):
    """
    按 账号(username) 聚合去重(同一账号=同一个人, 首行优先)
    返回 (rows, dup_count, conflict_msgs)
    - rows: 会被就地标记 dup_status ∈ {None,'duplicate','conflict'}
    - dup_count: 完全重复(部门/上级/职级完全一致)被跳过的行数
    - conflict_msgs: 冲突描述(部门/上级/职级不一致, 保留首行, 其余跳过)
    """
    seen = {}
    dup_count = 0
    conflict_msgs = []

    def key(r):
        return (r.get("dept"), r.get("parent"), r.get("tier"))

    for r in rows:
        r["dup_status"] = None
        if r.get("errors") or not r.get("username"):
            continue
        uname = r["username"]
        if uname in seen:
            if key(seen[uname]) == key(r):
                dup_count += 1
                r["dup_status"] = "duplicate"
            else:
                conflict_msgs.append(
                    _("Duplicate rows for account {} with different dept/parent/tier. Keeping the first occurrence.").format(uname)
                    + _(" (dept={}, tier={})").format(seen[uname].get('dept'), seen[uname].get('tier'))
                )
                r["dup_status"] = "conflict"
            continue
        seen[uname] = r
    return rows, dup_count, conflict_msgs


def _set_user_tier_role(user, role):
    """用户职级角色互斥: 只保留一个职级角色(经理/主管/员工), 不叠加; 其它非职级角色不受影响"""
    tier_keys = set(TIER_ROLE_KEY.values())
    for r in list(user.role.filter(key__in=tier_keys)):
        if r.id != role.id:
            user.role.remove(r)
    if role and not user.role.filter(id=role.id).exists():
        user.role.add(role)
    user.current_role = role


def preview(tenant, rows):
    """
    预览(dry_run): 分析将新建多少部门/用户, 并反馈错误/重复/冲突
    返回: {rows, stats, errors}
    """
    import copy

    from django.conf import settings
    from dvadmin.system.models import Dept, Users

    from application import dispatch

    default_password = dispatch.get_system_config_values("base.default_password") or "admin123456"

    rows = [copy.deepcopy(r) for r in rows]
    # 1) 账号去重(首行优先), 标记重复/冲突
    rows, dup_count, conflict_msgs = _group_duplicates(rows)

    errors = [{"row": i + 1, "msg": r["errors"]} for i, r in enumerate(rows) if r["errors"]]

    # 2) 过滤: 校验失败或完全重复/冲突的行不计入人数; 纯部门行只建部门不属人员
    valid = [r for r in rows if not r["errors"] and not r["dup_status"] and not r.get("is_dept_only")]

    # 2.5) 标记已存在账号(前端据此决定是否显示"新账号默认密码"提示)
    usernames = {r["username"] for r in valid}
    existing_users = Users.objects.filter(username__in=usernames)
    existing_set = set(existing_users.values_list("username", flat=True))
    for r in rows:
        if r.get("username") in existing_set:
            r["is_existing"] = True

    # 3) 其它租户账号冲突
    tenant_conflict = [u.username for u in existing_users if u.tenant_id and u.tenant_id != tenant.id]
    for uname in tenant_conflict:
        errors.append({"row": None, "msg": _("Account {} already belongs to another tenant, please use a different one.").format(uname)})
    for msg in conflict_msgs:
        errors.append({"row": None, "msg": msg})

    final = [r for r in valid if r["username"] not in tenant_conflict]
    existing_count = existing_users.filter(username__in=[r["username"] for r in final]).count()
    user_update = existing_count
    user_new = len(final) - user_update

    # 4) 部门统计(含纯部门行; 排除挂在公司根的行)
    dept_names = {
        r["dept"] for r in rows
        if r["dept"] and not r["errors"] and not _is_company_dept(r["dept"], tenant)
    }
    existing_depts = set(
        Dept.objects.filter(tenant=tenant, name__in=dept_names).values_list("name", flat=True)
    )
    dept_only_rows = sum(1 for r in rows if r.get("is_dept_only") and not r.get("errors"))

    row_error_count = sum(1 for e in errors if e["row"] is not None)
    stats = {
        "dept_new": len(dept_names - existing_depts),
        "dept_exist": len(existing_depts & dept_names),
        "dept_total": Dept.objects.filter(tenant=tenant).count(),
        "user_new": user_new,
        "user_update": user_update,
        "user_conflict": len(tenant_conflict),
        "duplicate_rows": dup_count,
        "conflict_rows": len(conflict_msgs),
        "dept_only_rows": dept_only_rows,
        "valid_rows": len(final),
        "invalid_rows": row_error_count,
    }
    return {"rows": rows, "stats": stats, "errors": errors, "default_password": default_password}


def apply(tenant, rows):
    """
    正式导入(dry_run=False): 建部门 → 建/更新用户 → 绑职级角色 → 归属租户
    - 同一账号去重(首行优先)
    - 职级角色互斥(经理/主管/员工只留一个)
    返回: 导入结果统计 + 默认密码提示
    """
    from django.conf import settings
    from dvadmin.system.models import Dept, Users

    from application import dispatch

    # 导入时自动确保三角色存在并授权按钮+data_range(避免新租户角色无权限/数据范围错误)
    roles = ensure_tenant_tier_roles(tenant)
    memo = {}
    created_depts = []
    default_password = dispatch.get_system_config_values("base.default_password") or "admin123456"

    # 认证约定(勿改): 前端登录把明文 md5 后上传, CustomBackend 也做 md5 回退 → 实际认证的密码 = md5(明文)。
    # 因此这里用 set_password(明文): 内部再 md5 一次即存 pbkdf2(md5(明文)), 与前端/后端认证语义一致, 用户即按明文 default_password 登录。

    # 去重(与 preview 一致): 完全重复/冲突的行跳过, 不落库
    _, dup_count, conflict_msgs = _group_duplicates(rows)
    user_new, user_update = 0, 0
    dept_new = 0

    with transaction.atomic():
        processed = set()
        for row in rows:
            if row.get("errors") or row.get("dup_status"):
                continue
            # 公司根行(部门值=公司名/公司标记): 不建部门, 直接挂在公司根
            if _is_company_dept(row["dept"], tenant):
                dept = None
            else:
                # 部门始终创建(含纯部门行)
                dept, is_new = _ensure_dept(tenant, row["dept"], row["parent"], memo, created_depts)
                if is_new:
                    dept_new += 1

            # 纯部门行: 只建部门, 不建账号
            if row.get("is_dept_only"):
                continue

            uname = row["username"]
            if uname in processed:  # 安全兜底
                continue
            processed.add(uname)

            user = Users.objects.filter(username=uname).first()
            is_new_user = False
            if not user:
                user = Users(username=uname)
                is_new_user = True
            # 归属租户 + 基础信息
            user.tenant = tenant
            user.name = row["name"] or user.name
            if row.get("mobile"):
                user.mobile = row["mobile"]
            # 账号为邮箱时, 同步写入 email 字段(为将来"邮箱登录/通知"做准备)
            if "@" in uname:
                user.email = uname
            user.dept = dept
            if is_new_user:
                user.is_active = True
                user.user_type = 1  # 前台用户
                user.set_password(default_password)
                user.save()
                user_new += 1
            else:
                user.save()
                user_update += 1
            # 绑定职级角色(互斥, 只留一个)
            role = roles.get(row["tier"])
            _set_user_tier_role(user, role)
            user.save()

    return {
        "tenant": {"id": tenant.id, "name": tenant.name},
        "dept_new": dept_new,
        "dept_total": Dept.objects.filter(tenant=tenant).count(),
        "user_new": user_new,
        "user_update": user_update,
        "user_total": Users.objects.filter(tenant=tenant).count(),
        "duplicate_rows": dup_count,
        "conflict_rows": len(conflict_msgs),
        "default_password": default_password,
    }


def _member_data_range(user):
    """取用户职级角色的数据范围档位(3本租户/1本部门及以下/0仅本人), 返回原始数字供前端 i18n 翻译"""
    from dvadmin.system.models import RoleMenuButtonPermission
    role = getattr(user, "current_role", None)
    if not role:
        roles = user.role.filter(key__in=TIER_ROLE_KEY.values())
        role = roles.first() if roles.exists() else None
    if not role:
        return None
    # 该角色在任意按钮上的 data_range(预设时统一按档位写)
    dr = RoleMenuButtonPermission.objects.filter(role=role).values_list("data_range", flat=True).first()
    return dr


def build_tree(tenant):
    """构建租户组织树: 根=公司, 节点=部门, 部门下带 members(员工)"""
    from dvadmin.system.models import Dept, Users

    depts = Dept.objects.filter(tenant=tenant).select_related("parent")
    dept_map = {d.id: {"id": d.id, "name": d.name, "type": "dept", "owner": d.owner,
                       "phone": d.phone, "parent": d.parent_id, "children": [], "members": []}
                for d in depts}
    roots = []
    for d in depts:
        node = dept_map[d.id]
        if d.parent_id and d.parent_id in dept_map:
            dept_map[d.parent_id]["children"].append(node)
        else:
            roots.append(node)

    users = Users.objects.filter(tenant=tenant).select_related("dept", "current_role")
    root_members = []
    for u in users:
        node = dept_map.get(u.dept_id)
        member = {
            "id": u.id, "name": u.name, "username": u.username,
            "mobile": u.mobile,
            "dept_id": u.dept_id,
            "is_active": u.is_active,
            "tier": getattr(u.current_role, "key", None),
            "tier_label": getattr(u.current_role, "name", None),
            "data_range": _member_data_range(u),
        }
        if node:
            node["members"].append(member)
        else:
            root_members.append(member)  # 挂在公司根(无部门)的员工

    def sort_nodes(nodes):
        for n in nodes:
            if n["type"] == "dept":
                sort_nodes(n["children"])
        nodes.sort(key=lambda x: (x["type"] != "dept", x.get("name") or ""))

    sort_nodes(roots)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "tenant_code": tenant.tenant_code,
        "type": "tenant",
        "children": roots,
        "members": root_members,
    }


# ==================== 组织架构 树内联 CRUD ==================== #


def _sibling_sort(tenant, parent_id):
    from dvadmin.system.models import Dept

    last = Dept.objects.filter(tenant=tenant, parent_id=parent_id).order_by("-sort").first()
    return (last.sort + 1) if last else 1


def create_or_update_dept(tenant, dept_id=None, name="", parent_id=None):
    """新建/重命名部门; parent_id 为空表示挂在公司根"""
    from dvadmin.system.models import Dept

    if not name:
        raise ValueError(_("Dept name is required"))
    parent = None
    if parent_id:
        parent = Dept.objects.filter(id=parent_id, tenant=tenant).first()
        if not parent:
            raise ValueError(_("Parent dept does not exist"))
    if dept_id:
        dept = Dept.objects.filter(id=dept_id, tenant=tenant).first()
        if not dept:
            raise ValueError(_("Dept does not exist"))
        dept.name = name
        dept.parent = parent
        dept.save(update_fields=["name", "parent"])
        return dept
    dept = Dept.objects.create(
        tenant=tenant,
        name=name,
        key=_dept_key(tenant, name),
        parent=parent,
        sort=_sibling_sort(tenant, parent_id),
        status=True,
    )
    dept.dept_belong_id = dept.id
    dept.save(update_fields=["dept_belong_id"])
    return dept


def delete_dept(tenant, dept_id):
    """删除部门(有子部门/成员则拒绝)"""
    from dvadmin.system.models import Dept, Users

    dept = Dept.objects.filter(id=dept_id, tenant=tenant).first()
    if not dept:
        raise ValueError(_("Dept does not exist"))
    if Dept.objects.filter(parent=dept).exists():
        raise ValueError(_("Please delete the sub-depts under this dept first"))
    if Users.objects.filter(dept=dept).exists():
        raise ValueError(_("Please move or delete the members of this dept first"))
    dept.delete()


def save_member(tenant, user_id=None, *, name="", username="", mobile="", dept_id=None,
                tier=None, is_active=True):
    """新建/编辑成员(职级角色互斥); dept_id 为空表示挂在公司根"""
    from dvadmin.system.models import Dept, Users

    from application import dispatch

    # 用 ensure_tenant_tier_roles 确保三角色存在且已含按钮/菜单授权(树形编辑器逐个加人路径也必须自动授权)
    roles = ensure_tenant_tier_roles(tenant)
    role = roles.get(_normalize_tier(tier) or "")
    if tier and not role:
        raise ValueError(_("Unrecognized tier: {}").format(tier))

    now = dispatch.get_system_config_values("base.default_password") or "admin123456"
    dept = None
    if dept_id:
        dept = Dept.objects.filter(id=dept_id, tenant=tenant).first()
        if not dept:
            raise ValueError(_("Dept does not exist"))

    if user_id:
        user = Users.objects.filter(id=user_id, tenant=tenant).first()
        if not user:
            raise ValueError(_("Member does not exist"))
        if name:
            user.name = name
        if mobile:
            user.mobile = mobile
        user.dept = dept
        user.is_active = is_active
        user.save()
    else:
        if not username:
            raise ValueError(_("Account is required"))
        if Users.objects.filter(username=username).exists():
            raise ValueError(_("Account {} already exists").format(username))
        if not re.fullmatch(r"[A-Za-z0-9@\._\-+]+", username):
            raise ValueError(_("Account contains invalid characters (only letters/numbers/underscore/hyphen/dot/@ allowed)"))
        if "@" not in username or "." not in username.split("@")[-1]:
            raise ValueError(_("Login account must be an email, e.g. name@example.com"))
        user = Users(username=username)
        user.tenant = tenant
        user.name = name or username
        if mobile:
            user.mobile = mobile
        user.dept = dept
        user.is_active = is_active
        user.user_type = 1
        # 认证约定: 前端/后端按 md5(明文) 认证, set_password(明文) 内部再 md5 => 存 pbkdf2(md5(明文)); 成员按明文默认密码登录
        user.set_password(now)
        user.save()
    if "@" in user.username:
        user.email = user.username
        user.save()
    # 职级角色(互斥)
    if role:
        _set_user_tier_role(user, role)
        user.save()
    return user


def delete_member(tenant, user_id):
    """删除成员; 需属于该租户"""
    from dvadmin.system.models import Users

    user = Users.objects.filter(id=user_id, tenant=tenant).first()
    if not user:
        raise ValueError(_("Member does not exist"))
    user.delete()
