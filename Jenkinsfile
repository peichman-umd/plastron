pipeline {
  // Jenkins configuration dependencies
  //
  //   Global Tool Configuration:
  //     Git
  //
  // This configuration utilizes the following Jenkins plugins:
  //
  //   * Warnings Next Generation
  //   * Email Extension Plugin
  //
  // This configuration also expects the following environment variables
  // to be set (typically in /apps/ci/config/env:
  //
  // JENKINS_EMAIL_SUBJECT_PREFIX
  //     The Email subject prefix identifying the server.
  //     Typically "[Jenkins - <HOSTNAME>]" where <HOSTNAME>
  //     is the name of the server, i.e. "[Jenkins - cidev]"
  //
  // JENKINS_DEFAULT_EMAIL_RECIPIENTS
  //     A comma-separated list of email addresses that should
  //    be the default recipients of Jenkins emails.

  agent {
    dockerfile {
      filename 'Dockerfile.ci'
      // Pass JENKINS_EMAIL_SUBJECT_PREFIX and JENKINS_DEFAULT_EMAIL_RECIPIENTS
      // into container as "env" arguments, so they are available inside the
      // Docker container
      args '-u root --env JENKINS_DEFAULT_EMAIL_RECIPIENTS=$JENKINS_DEFAULT_EMAIL_RECIPIENTS --env JENKINS_EMAIL_SUBJECT_PREFIX=$JENKINS_EMAIL_SUBJECT_PREFIX'
    }
  }

  options {
    buildDiscarder(
      logRotator(
        artifactDaysToKeepStr: '',
        artifactNumToKeepStr: '',
        numToKeepStr: '20'))
  }

  environment {
    DEFAULT_RECIPIENTS = "${ \
      sh(returnStdout: true, \
         script: 'echo $JENKINS_DEFAULT_EMAIL_RECIPIENTS').trim() \
    }"

    EMAIL_SUBJECT_PREFIX = "${ \
      sh(returnStdout: true, script: 'echo $JENKINS_EMAIL_SUBJECT_PREFIX').trim() \
    }"

    EMAIL_SUBJECT = "$EMAIL_SUBJECT_PREFIX - " +
                    '$PROJECT_NAME - ' +
                    'GIT_BRANCH_PLACEHOLDER - ' +
                    '$BUILD_STATUS! - ' +
                    "Build # $BUILD_NUMBER"

    EMAIL_CONTENT =
        '''$PROJECT_NAME - GIT_BRANCH_PLACEHOLDER - $BUILD_STATUS! - Build # $BUILD_NUMBER:
           |
           |Check console output at $BUILD_URL to view the results.
           |
           |There were ${TEST_COUNTS,var="fail"} failed tests.
           |
           |There are ${ANALYSIS_ISSUES_COUNT} static analysis issues in this build.
           |
           |There were ${TEST_COUNTS,var="skip"} skipped tests.'''.stripMargin()
  }

  stages {
    stage('initialize') {
      steps {
        script {
          // Retrieve the actual Git branch being built for use in email.
          //
          // For pull requests, the actual Git branch will be in the
          // CHANGE_BRANCH environment variable.
          //
          // For actual branch builds, the CHANGE_BRANCH variable won't exist
          // (and an exception will be thrown) but the branch name will be
          // part of the PROJECT_NAME variable, so it is not needed.

          ACTUAL_GIT_BRANCH = ''

          try {
            ACTUAL_GIT_BRANCH = CHANGE_BRANCH + ' - '
          } catch (groovy.lang.MissingPropertyException mpe) {
            // Do nothing. A branch (as opposed to a pull request) is being
            // built
          }

          // Replace the "GIT_BRANCH_PLACEHOLDER" in email variables
          EMAIL_SUBJECT = EMAIL_SUBJECT.replaceAll('GIT_BRANCH_PLACEHOLDER - ', ACTUAL_GIT_BRANCH )
          EMAIL_CONTENT = EMAIL_CONTENT.replaceAll('GIT_BRANCH_PLACEHOLDER - ', ACTUAL_GIT_BRANCH )
        }
      }
    }

    stage('build') {
      steps {
        sh '''
          python -m venv .venv
          . .venv/bin/activate

          pip install \
              -e './plastron-utils[test]' \
              -e './plastron-client[test]' \
              -e './plastron-rdf[test]' \
              -e './plastron-messaging[test]' \
              -e './plastron-models[test]' \
              -e './plastron-repo[test]' \
              -e './plastron-jobs[test]' \
              -e './plastron-web[test]' \
              -e './plastron-stomp[test]' \
              -e './plastron-cli[test]'
        '''
      }
    }

    stage('test') {
      steps {
        sh '''
          . .venv/bin/activate

          pytest -v --junitxml=reports/results.xml
        '''
      }
      post {
        always {
          junit '**/reports/results.xml'
        }
      }
    }

    stage('static-analysis') {
      steps {
        sh '''
          . .venv/bin/activate

          # Install pycodestyle
          pip install pycodestyle

          # Run pycodesytyle
          # Send output to standard out for "Record compiler warnings and static analysis results"
          # post-build action
          #
          # Using "|| true" so that build will be considered successful, even if there are violations.
          pycodestyle --format pylint . || true
        '''
      }
      post {
        always {
          // Collect pycodestyle reports
          recordIssues(tools: [pyLint(reportEncoding: 'UTF-8', name: 'pycodestyle')],
                       qualityGates: [[threshold: 1, type: 'TOTAL', criticality: 'UNSTABLE']]
          )
        }
      }
    }

    stage('clean-workspace') {
      steps {
        // Change permissions of the workspace directory to world-writeable
        // so Jenkins can delete it. This is needed, because files may be
        // written to the directory from the Docker container as the "root"
        // user, which Jenkins would not otherwise be able to clean up.
        sh '''
          chmod --recursive 777 $WORKSPACE
        '''

        cleanWs()
      }
    }
  }

  post {
    always {
      emailext to: "$DEFAULT_RECIPIENTS",
               subject: "$EMAIL_SUBJECT",
               body: "$EMAIL_CONTENT"
    }
  }
}
