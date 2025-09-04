from jinja2 import Environment, FileSystemLoader


def render_template(name, context, template_root):
    env = Environment(loader=FileSystemLoader(template_root))
    return env.get_template(name).render(context)


def timeago(tdelta):
    # https://github.com/hustcc/timeago (the good bits)
    # minute, hour, day, week, month, year(365 days)
    BUCKETS = [60.0, 60.0, 24.0, 7.0, 365.0 / 7.0 / 12.0, 12.0]
    TEMPLATES = [
        "just now",
        "%s seconds ago",
        "1 minute ago",
        "%s minutes ago",
        "1 hour ago",
        "%s hours ago",
        "1 day ago",
        "%s days ago",
        "1 week ago",
        "%s weeks ago",
        "1 month ago",
        "%s months ago",
        "1 year ago",
        "%s years ago",
    ]
    diff_seconds = int(tdelta.total_seconds())
    i = 0
    while i < len(BUCKETS):
        tmp = BUCKETS[i]
        if diff_seconds >= tmp:
            i += 1
            diff_seconds /= tmp
        else:
            break
    diff_seconds = int(diff_seconds)
    i *= 2

    # 'just now' is within 10s
    if diff_seconds > (9 if i == 0 else 1):
        i += 1

    template = TEMPLATES[i]
    return '%s' in template and template % diff_seconds or template
