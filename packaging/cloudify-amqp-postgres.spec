# due to a bug in psycopg2's 2.7.4 build, stripping their binaries must be disabled
%define debug_package %{nil}
%define __strip /bin/true

%global __requires_exclude_from site-packages/psycopg2
%global __provides_exclude_from site-packages/psycopg2

Name:           cloudify-amqp-postgres
Version:        %{CLOUDIFY_VERSION}
Release:        %{CLOUDIFY_PACKAGE_RELEASE}%{?dist}
Summary:        Cloudify's AMQP PostgreSQL Transport
Group:          Applications/Multimedia
License:        Apache 2.0
URL:            https://github.com/cloudify-cosmo/cloudify-amqp-postgres
Vendor:         Cloudify Platform Ltd.
Packager:       Cloudify Platform Ltd.

BuildRequires:  python >= 2.7, python-virtualenv
Requires:       python >= 2.7, postgresql-libs
Requires(pre):  shadow-utils

%define _venv /opt/amqp-postgres/env
%define _user amqppostgres


%description
Pulls Cloudify logs/events from RabbitMQ and posts them in PostgreSQL.


%build

virtualenv %_venv

%_venv/bin/pip install --upgrade pip setuptools
%_venv/bin/pip install --upgrade "${RPM_SOURCE_DIR}/"


%install

mkdir -p %{buildroot}/opt/amqp-postgres
mv %_venv %{buildroot}/opt/amqp-postgres

# Create the log dir
mkdir -p %{buildroot}/var/log/cloudify/amqp-postgres

# Copy static files into place. In order to have files in /packaging/files
# actually included in the RPM, they must have an entry in the %files
# section of this spec file.
cp -R ${RPM_SOURCE_DIR}/packaging/files/* %{buildroot}


%pre

groupadd -fr %_user
getent passwd %_user >/dev/null || useradd -r -g %_user -d /opt/amqp-postgres -s /sbin/nologin %_user


%files

%dir %attr(750,%_user,%_user) /opt/amqp-postgres
/opt/amqp-postgres/*
/opt/amqp-postgres_NOTICE.txt
/usr/lib/systemd/system/cloudify-amqp-postgres.service

/etc/logrotate.d/cloudify-amqp-postgres
%attr(750,%_user,adm) /var/log/cloudify/amqp-postgres