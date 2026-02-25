from reasoning.regulation_versions import REGULATION_VERSIONS

def validate_temporal_consistency(reasoning_map, event_date):
    if not event_date:
        return "REVIEW_REQUIRED"

    for node in reasoning_map:
        versions = REGULATION_VERSIONS.get(node.regulation, [])
        valid = False

        for v in versions:
            start = v["effective_from"]
            end = v["effective_to"]

            if start <= event_date.isoformat() and (end is None or event_date.isoformat() <= end):
                node.regulation_version = v["version"]
                valid = True
                break

        if not valid:
            raise ValueError(
                f"Article {node.article} not valid at time of event"
            )
