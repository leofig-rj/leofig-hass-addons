# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

ARG BUILD_DATE
ARG BUILD_REF
ARG BUILD_VERSION
ARG BUILD_ARCH

# Labels
LABEL \
    io.hass.name="LoRa2MQTT - Integration of LoRa with Home Assistant using MQTT" \
    io.hass.description="Integration of LoRa with Home Assistant using MQTT" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="leofig_rj <leoagfig@gmail.com>" \
    org.label-schema.description="Integration of LoRa with Home Assistant using MQTT" \
    org.label-schema.build-date=${BUILD_DATE} \
    org.label-schema.name="LoRa2MQTT" \
    org.label-schema.schema-version="0.0.1" \
    org.label-schema.url="https://github.com/leofig-rj/leofig-hass-addons" \
    org.label-schema.usage="https://github.com/leofig-rj/leofig-hass-addons/blob/master/lora2mqtt/README.md" \
    org.label-schema.vcs-ref=${BUILD_REF} \
    org.label-schema.vcs-url="https://github.com/leofig-rj/leofig-hass-addons" \
    org.label-schema.vendor="Hass.io Add-on"

# Copy root filesystem
COPY rootfs /

# Install requirements
RUN pip3 install -r /tmp/requirements.txt

# Define volumes para acesso no container
VOLUME [ "/share", "/config" ]

# Set execution permissions
RUN chmod a+x /etc/services.d/lora2mqtt/run
RUN chmod a+x /etc/services.d/lora2mqtt/finish
