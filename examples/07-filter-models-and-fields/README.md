# Example 7 - Filter models and fields

In some cases you might want to subclass existing `DiffSyncModel` classes in order to change their behavior.
While doing this, you might also want to remove attributes from those classes which you don't care about in your
implementation, but the original class cares about. This is where `diffsync.helpers.filter_model_fields` comes into
play. This class decorator allows you to filter specific fields from being included in the model, such as the
`description` field in the example for the Site model.