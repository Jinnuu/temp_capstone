from .rbac import capabilities, required_capability, approval_mode, roles, ROLE_LABELS, is_main, public_signup_requires_approval


def access_context(request):
    caps = capabilities(request.user)
    match = getattr(request, 'resolver_match', None)
    write_cap = required_capability(match.view_name, 'POST') if match else None
    return {'public_signup_requires_approval': public_signup_requires_approval(), 'snp_main_admin': is_main(request.user), 'snp_role_summary': ', '.join(ROLE_LABELS[name] for name in sorted(roles(request.user))), 'account_approval_mode': approval_mode(), 'snp_caps': caps, 'snp_admin': 'accounts.manage' in caps, 'snp_readonly': bool(request.user.is_authenticated and write_cap and write_cap not in caps)}
