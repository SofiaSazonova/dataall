ENV_TYPE = """
environmentUri
created
userRoleInEnvironment
description
name
label
AwsAccountId
region
owner
tags
SamlGroupName
EnvironmentDefaultBucketName
EnvironmentDefaultIAMRoleArn
EnvironmentDefaultIAMRoleName
EnvironmentDefaultIAMRoleImported
resourcePrefix
subscriptionsEnabled
subscriptionsProducersTopicImported
subscriptionsConsumersTopicImported
subscriptionsConsumersTopicName
subscriptionsProducersTopicName
organization {
  organizationUri
  label
  name
}
stack {
  stack
  status
  stackUri
  targetUri
  accountid
  region
  stackid
  link
  outputs
  resources
}
networks {
  VpcId
  privateSubnetIds
  publicSubnetIds
}
parameters {
  key
  value
}
"""


def create_environment(client, name, group, organizationUri, awsAccountId, region, tags):
    query = {
        'operationName': 'CreateEnvironment',
        'variables': {
            'input': {
                'label': name,
                'SamlGroupName': group,
                'organizationUri': organizationUri,
                'AwsAccountId': awsAccountId,
                'region': region,
                'description': 'Created for integration testing',
                'tags': tags,
            }
        },
        'query': f"""
                    mutation CreateEnvironment($input: NewEnvironmentInput!) {{
                      createEnvironment(input: $input) {{
                        {ENV_TYPE}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.createEnvironment


def get_environment(client, environmentUri):
    query = {
        'operationName': 'GetEnvironment',
        'variables': {'environmentUri': environmentUri},
        'query': f"""
                    query GetEnvironment($environmentUri: String!) {{
                      getEnvironment(environmentUri: $environmentUri) {{
                        {ENV_TYPE}  
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.getEnvironment


def delete_environment(client, environmentUri, deleteFromAWS=True):
    query = {
        'operationName': 'deleteEnvironment',
        'variables': {
            'environmentUri': environmentUri,
            'deleteFromAWS': deleteFromAWS,
        },
        'query': """
                    mutation deleteEnvironment(
                      $environmentUri: String!
                      $deleteFromAWS: Boolean
                    ) {
                      deleteEnvironment(
                        environmentUri: $environmentUri
                        deleteFromAWS: $deleteFromAWS
                      )
                    }
                """,
    }
    response = client.query(query=query)
    return response


def update_environment(client, environmentUri, input: dict):
    query = {
        'operationName': 'UpdateEnvironment',
        'variables': {
            'environmentUri': environmentUri,
            'input': input,
        },
        'query': f"""
                    mutation UpdateEnvironment(
                      $environmentUri: String!
                      $input: ModifyEnvironmentInput!
                    ) {{
                      updateEnvironment(environmentUri: $environmentUri, input: $input) {{
                        {ENV_TYPE}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.updateEnvironment


def list_environments(client, term=''):
    query = {
        'operationName': 'ListEnvironments',
        'variables': {
            'filter': {'term': term},
        },
        'query': f"""
                    query ListEnvironments($filter: EnvironmentFilter) {{
                      listEnvironments(filter: $filter) {{
                        count
                        page
                        pages
                        hasNext
                        hasPrevious
                        nodes {{
                            {ENV_TYPE}
                        }}
                      }}
                    }}
                """,
    }
    response = client.query(query=query)
    return response.data.listEnvironments
