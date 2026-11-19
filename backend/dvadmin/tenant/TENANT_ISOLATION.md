# 多租户隔离（Tenant）实施说明与风险提示

> 本项目为「轻量 SaaS」，采用**单库单表逻辑租户隔离**（不使用 django-tenant-schemas / 不做 schema 隔离）。
> 一个 `Tenant` = 一家泰国房产中介/物业公司。所有业务数据通过 `tenant` 字段做第一层硬隔离；现有部门/角色/按钮权限是第二层业务权限，两者叠加。

## 一、核心组件（都在 `dvadmin/tenant`）

| 组件 | 文件 | 说明 |
| --- | --- | --- |
| `Tenant` 模型 | `models.py` | 租户(公司)：name / tenant_code(唯一) / contact / google_calendar_id / plan_type(trial·paid) / is_active / expire_time / remark |
| `TenantModel` 抽象基类 | `models.py` | 所有业务模型的基类，自动带 `tenant` 外键(PROTECT) + CoreModel 审计字段 |
| `TenantModelViewSet` 基类 | `views.py` | 所有业务 ViewSet 的基类：`get_queryset()` 按 `request.user.tenant` 过滤(超管返回全部)；非租户用户返回空集 |
| `TenantModelSerializerMixin` | `serializers.py` | `tenant` 字段只读(禁止前端传入)，`create()` 时后端从请求用户注入 tenant |
| `get_tenant_queryset(tenant_id, qs)` | `views.py` | Celery 定时任务等无 request 场景下按租户过滤；不传 tenant_id 返回空集(防全表扫描越权) |

`Users` 模型已增加 `tenant` 外键（超管为 null，可见全部租户）与 `google_calendar_id`（每中介的 Google 日历）。

> ## 🔑 Bot 归属与多租户关系（重要）
> - **`LineBot.tenant`**：每个 Bot 只能归属一个租户（`tenant=null` 为平台默认/演示 bot）。Bot 是租户私有，**不跨租户**。
> - **`Property.line_bot`**：每套房源(群)指定用哪个 bot（可为空=用租户名下 bot）。`Tenant.line_bot` 字段**已废弃**（改为多 bot，由 bot 归属 + 房源指定）。
> - **取 bot 优先级**：`get_bot_for_property(prop)` = 房源.line_bot(且归属匹配) → 租户名下任一启用 bot → 全局默认。
> - **防串台硬校验**：房源绑定时 `PropertySerializer.validate_line_bot` 强制 `line_bot.tenant == 房源.tenant`（或平台默认 bot），违规直接拒绝。推送前 `tasks.scan_and_notify` 再校验一次归属，双重保险。
> - **Bot 下拉隔离**：`LineBotViewSet.options` 非超管只见「本租户 bot + 平台默认 bot(is_default)」，不暴露空闲未分配 bot。

> ## 🔑 RBAC 角色租户隔离（重要）
> - **`Role.tenant`**：角色现在带租户。`tenant=null` = 平台模板角色（超管建，各租户可套用）；`tenant=某租户` = 该租户自己的角色。**角色按租户隔离**，租户管理员只能管理自己租户的角色。
> - **`(tenant,key)` 联合唯一**：同租户内 `key` 唯一；不同租户可同名角色。
> - **`RoleViewSet.get_queryset`**：超管看全部；租户用户只看 `tenant=自己 | tenant__isnull(平台模板)`。
> - **角色-用户 action** (`set_role_users`/`get_role_users`/`add_role_users`/`remove_role_user`)：非超管限本租户用户，且 role 必须属本租户(或平台模板)。
> - **角色下拉**：新增 `RoleViewSet.options`（按租户过滤），前端用户页角色下拉改用 `/api/system/role/options/`。
> - **登录后菜单/按钮权限** (`web_router`/`menu_button_all_permission`) 靠 `user.role` 派生——角色已按租户隔离，若用户只被授予本租户角色，权限自然限于本租户，**无需改这两个接口**。
> - ⚠️ **超管** 仍全局可见所有角色/菜单/租户（`is_superuser` 分支保持）。现有 3 个平台模板角色（管理员/用户/中介经理）均为 `tenant=null`，可被任意租户套用。

> ## 🔑 租户内部数据范围（Data Scope，重要）
> 「经理/主管/员工」**不看菜单差别，只看数据范围**（数据级隔离），叠加在租户隔离之上。
> - **`Property.owner`（负责人）**：房源归属人，创建缺省=创建人，可指派给他人（员工负责的房源 = 自己创建的 + 被指派的）。
> - **`Dept.tenant`（部门/组按租户隔离)**：部门名按租户去重，`A公司-中介一组` 与 `B公司-中介一组` 互不干扰。'主管管的人' = 同部门(含子部门)下的用户。
> - **预设三档角色（每租户自动带）**：`tenant_manager`(租户经理) / `tenant_supervisor`(租户主管) / `tenant_emp`(租户员工)；`init_tenant_roles` 命令创建并给三角色授予全部业务接口按钮权限(接口级可访问)，并按档位预设 `data_range`：manager=3(本租户全部) / supervisor=1(本部门及以下) / emp=0(仅本人)。旧 `agent_manager`(中介经理) 由 `init_property_menu` 预设 data_range=3(全部)。
> - **数据范围 `OwnerDataLevelFilter`+`RoleMenuButtonPermission.data_range`（配置驱动，按钮级）**：业务 ViewSet 继承 `OwnerScopeViewSetMixin`（含租户硬隔离 + 该过滤器）。`data_range` 在业务数据上是 **owner 维度**（负责人：有 owner 用 owner，否则回退 creator；两者皆无则返回空集=fail-closed）。语义：`0 仅本人 / 1 本部门及以下 / 2 本部门 / 3 本租户全部 / 4 自定义(部门集合)`；用户恒可见自己负责/创建的数据。⚠️ 此口径与原版 **dept 口径(data_range 按 dept_belong_id)不同**，仅平台模板角色/非业务表才走 dept 口径。
> - ⚠️ **关键**：业务 ViewSet 继承 `OwnerScopeViewSetMixin` 后 `extra_filter_class=[CoreModelFilterBankend, OwnerDataLevelFilter]`（替换系统默认 `DataLevelPermissionMargeFilter`，避免其按 `dept_belong_id` 与 owner 范围冲突）。Dept 等非 owner 模型不要用该 mixin。

## 二、⚠️ 风险提示（重要，务必遵守）

1. **新增业务表必须继承 `TenantModel`**，且序列化器必须使用 `TenantModelSerializerMixin`。
   - 否则该表没有 `tenant` 字段，租户隔离失效 → **数据越权泄露**。
2. **新增业务 ViewSet 必须继承 `TenantModelViewSet`，禁止直接继承原生 `CustomModelViewSet`。**
   - 只有 `TenantModelViewSet` 才强制按租户过滤；直接继承原生会让跨租户数据互通。
3. **禁止前端传入 `tenant`**：`tenant` 在序列化器里是 `read_only`，后端完全由登录用户上下文注入。
4. **定时任务必须显式传 `tenant_id`**，用 `get_tenant_queryset(tenant_id, ...)`，不得无租户全表扫描。
5. **租户管理接口 `TenantViewSet` 仅超管可操作**（`SuperuserPermission`），普通用户访问返回 code 4000。
6. 超级管理员(tenant=null)在业务接口中看到的仍是"全部"；普通用户只能看到自己租户的数据。

## 三、如何新增一个租户隔离的业务模块（步骤）

1. 新建 app（如 `dvadmin/property`），`INSTALLED_APPS` 注册。
2. 模型继承 `TenantModel`：
   ```python
   from dvadmin.tenant.models import TenantModel
   class Property(TenantModel):
       name = models.CharField(...)
   ```
3. 序列化器继承 / 混入：
   ```python
   from dvadmin.tenant.serializers import TenantModelSerializerMixin
   class PropertySerializer(TenantModelSerializerMixin, CustomModelSerializer):
       class Meta:
           model = Property
           fields = "__all__"
   ```
4. 视图继承：
   ```python
   from dvadmin.tenant.views import OwnerScopeViewSetMixin
   class PropertyViewSet(OwnerScopeViewSetMixin):
       queryset = Property.objects.all()
       serializer_class = PropertySerializer
   ```
   （若该业务表没有 owner 字段但有 creator，过滤器会自动回退 creator；两者皆无则默认拒绝/空集。）
5. 注册路由，迁移：`python manage.py makemigrations property && python manage.py migrate`。

## 四、数据库迁移顺序

项目已切换至 **PostgreSQL**（`env.py`：`DATABASE_ENGINE=postgresql`，host 127.0.0.1:5433，库 `dvadmin`）。

新装/重装迁移顺序：
```bash
python manage.py migrate              # 先迁移所有已有 app
python manage.py makemigrations tenant system   # 生成租户 app + Users.tenant 的迁移
python manage.py migrate              # 应用
python manage.py init_area            # 地区数据
python manage.py init -y              # 系统初始化 + 超管
python manage.py init_tenant_menu     # 生成「租户管理」菜单(仅超管可见)
```

注意：`tenant.0001_initial` 必须先于 `system.0003_users_...tenant`，因为 Users.tenant 外键引用 tenant.Tenant。

## 五、当前已验证
- 超管可创建/查询/编辑租户；普通用户访问租户接口被拒(4000)。
- 超管创建用户可绑定租户；`tenant_name` 正常输出；普通用户强行绑租户会被置空(仅超管可绑定)。
- 前端新增「租户管理」页(仅超管菜单可见)，提供公司名称/租户标识/联系人/电话/客户类型(试用·正式)/状态/到期时间/Google日历ID/备注的增删改查。
- 用户管理页新增「所属租户」字段(仅超管可设置)。
