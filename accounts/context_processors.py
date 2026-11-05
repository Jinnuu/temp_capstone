from .rbac import capabilities, required_capability, approval_mode


def access_context(request):
    caps = capabilities(request.user)
    match = getattr(request, 'resolver_match', None)
    write_cap = required_capability(match.view_name, 'POST') if match else None
    return {'account_approval_mode': approval_mode(), 'snp_caps': caps, 'snp_admin': 'accounts.manage' in caps, 'snp_readonly': bool(request.user.is_authenticated and write_cap and write_cap not in caps)}
