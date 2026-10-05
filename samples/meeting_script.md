# Sample Meeting Script

Maya:  Okay, let's get started. Thanks for joining, Priya and Dan. Three things today: the session cache, the gRPC question, and audit prep.
Priya: On the session cache, we're still on Memcached, and p99 latency on login is around three hundred forty milliseconds. Our SLA says under two hundred fifty.
Dan:   Redis would fix that. In staging we saw p99 drop to about ninety milliseconds.
Maya:  Any objections to moving the session cache to Redis?
Priya: None from me.
Dan:   Same, none.
Maya:  Okay, then it's decided. We migrate the session cache from Memcached to Redis.
Maya:  Dan, can you write the Terraform module for the Redis cluster?
Dan:   Yes, I'll have the Terraform module done by Thursday.
Maya:  Great. We'll roll it out on the Kubernetes staging cluster first with a canary deployment, five percent of traffic.
Priya: Sounds right. I'd also suggest we move all internal services from REST to gRPC.
Dan:   That would cut serialization overhead, but it's a big change for the mobile team.
Maya:  I don't want to decide that today. Let's revisit gRPC next sprint, once we have numbers.
Priya: Fine by me.
Maya:  On PostgreSQL, we are not going to upgrade to version sixteen this quarter. The risk is too high before the audit.
Dan:   Agreed.
Priya: Right, the upgrade waits until next quarter.
Maya:  Priya, can you update the OAuth scopes documentation?
Priya: Sure, I'll take that. No date yet, I need to see how big it is.
Maya:  Fine. Now audit prep. The audit is on the fifteenth. Someone has to rotate the staging database credentials before then.
Dan:   Yeah, that needs doing.
Maya:  Okay, I'll leave that open for now. We need to work out who has time.
Maya:  Dan, maybe you could also look at the Grafana dashboards if you get time.
Dan:   We'll see.
Priya: One more thing: the Kafka consumer lag alert fired twice last week.
Maya:  Noted. No action on that for now.
Maya:  Last thing, we have twelve thousand dollars approved for the Redis cluster, and we must not exceed that.
Dan:   Understood.
Maya:  Thanks everyone. That's it.
