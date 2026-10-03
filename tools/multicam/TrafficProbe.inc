// Count network-source buffers once, before depayloading/decoding. RTSP uses
// internal udpsrc elements for RTP and RTCP, including packets dropped later.
using TrafficCounter = std::shared_ptr<std::atomic<quint64>>;
static GstPadProbeReturn countNetworkBuffer(GstPad *, GstPadProbeInfo *info, gpointer data) {
    quint64 bytes = 0;
    if (GST_PAD_PROBE_INFO_TYPE(info) & GST_PAD_PROBE_TYPE_BUFFER) {
        if (GstBuffer *buffer = gst_pad_probe_info_get_buffer(info)) bytes = gst_buffer_get_size(buffer);
    } else if (GST_PAD_PROBE_INFO_TYPE(info) & GST_PAD_PROBE_TYPE_BUFFER_LIST) {
        if (GstBufferList *list = gst_pad_probe_info_get_buffer_list(info)) {
            for (guint i = 0; i < gst_buffer_list_length(list); ++i)
                bytes += gst_buffer_get_size(gst_buffer_list_get(list, i));
        }
    }
    (*static_cast<TrafficCounter *>(data))->fetch_add(bytes, std::memory_order_relaxed);
    return GST_PAD_PROBE_OK;
}
static void attachTrafficCounter(GstElement *source, const TrafficCounter &counter) {
    GstPad *pad = gst_element_get_static_pad(source, "src");
    if (!pad) return;
    gst_pad_add_probe(pad, static_cast<GstPadProbeType>(GST_PAD_PROBE_TYPE_BUFFER | GST_PAD_PROBE_TYPE_BUFFER_LIST),
        countNetworkBuffer, new TrafficCounter(counter), [](gpointer p) { delete static_cast<TrafficCounter *>(p); });
    gst_object_unref(pad);
}
static void attachRtspTrafficCounter(GstBin *, GstBin *, GstElement *element, gpointer data) {
    GstElementFactory *factory = gst_element_get_factory(element);
    if (factory && g_strcmp0(gst_plugin_feature_get_name(GST_PLUGIN_FEATURE(factory)), "udpsrc") == 0)
        attachTrafficCounter(element, *static_cast<TrafficCounter *>(data));
}
