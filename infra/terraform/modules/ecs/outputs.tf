output "api_alb_dns"             { value = aws_lb.api.dns_name }
output "web_alb_dns"             { value = aws_lb.web.dns_name }
output "task_security_group_id"  { value = aws_security_group.task.id }
output "cluster_name"            { value = aws_ecs_cluster.main.name }
output "api_service_name"        { value = aws_ecs_service.api.name }
output "web_service_name"        { value = aws_ecs_service.web.name }
output "celery_service_name"     { value = aws_ecs_service.celery.name }
